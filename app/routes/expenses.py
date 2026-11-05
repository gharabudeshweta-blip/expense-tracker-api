"""Routes for creating and managing expenses."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import db
from app.models import Expense
from app.utils import (
    ALLOWED_CATEGORIES,
    error_response,
    parse_iso_date,
    parse_positive_integer,
    read_json_object,
    validate_expense_data,
)

expenses_bp = Blueprint("expenses", __name__, url_prefix="/expenses")


def _expense_json(expense):
    return {
        "id": expense.id,
        "title": expense.title,
        "amount": str(expense.amount),
        "category": expense.category,
        "expense_date": expense.expense_date.isoformat(),
        "note": expense.note,
        "created_at": expense.created_at.isoformat(),
        "updated_at": expense.updated_at.isoformat(),
    }


def _find_user_expense(expense_id):
    return Expense.query.filter_by(
        id=expense_id,
        user_id=int(get_jwt_identity()),
    ).first()


@expenses_bp.post("")
@jwt_required()
def create_expense():
    data, error = read_json_object()
    if error:
        return error_response(error, 400)

    fields, error = validate_expense_data(data)
    if error:
        return error_response(error, 400)

    expense = Expense(
        user_id=int(get_jwt_identity()),
        **fields,
    )
    db.session.add(expense)
    db.session.commit()

    return jsonify(
        message="Expense created successfully.",
        expense=_expense_json(expense),
    ), 201


@expenses_bp.get("/<int:expense_id>")
@jwt_required()
def get_expense(expense_id):
    expense = _find_user_expense(expense_id)
    if expense is None:
        return error_response("Expense not found.", 404)
    return jsonify(expense=_expense_json(expense)), 200


@expenses_bp.put("/<int:expense_id>")
@jwt_required()
def update_expense(expense_id):
    expense = _find_user_expense(expense_id)
    if expense is None:
        return error_response("Expense not found.", 404)
    data, error = read_json_object()
    if error:
        return error_response(error, 400)

    fields, error = validate_expense_data(data)
    if error:
        return error_response(error, 400)

    for field, value in fields.items():
        setattr(expense, field, value)
    db.session.commit()

    return jsonify(
        message="Expense updated successfully.",
        expense=_expense_json(expense),
    ), 200


@expenses_bp.delete("/<int:expense_id>")
@jwt_required()
def delete_expense(expense_id):
    expense = _find_user_expense(expense_id)
    if expense is None:
        return error_response("Expense not found.", 404)

    db.session.delete(expense)
    db.session.commit()
    return jsonify(message="Expense deleted successfully."), 200


@expenses_bp.get("")
@jwt_required()
def list_expenses():
    user_id = int(get_jwt_identity())
    query = Expense.query.filter_by(user_id=user_id)

    category = request.args.get("category")
    if category is not None:
        if category not in ALLOWED_CATEGORIES:
            return error_response("Invalid category filter.", 400)
        query = query.filter_by(category=category)

    from_date = request.args.get("from_date")
    if from_date is not None:
        parsed_from_date, error = parse_iso_date(from_date, "from_date")
        if error:
            return error_response(error, 400)
        query = query.filter(Expense.expense_date >= parsed_from_date)

    to_date = request.args.get("to_date")
    if to_date is not None:
        parsed_to_date, error = parse_iso_date(to_date, "to_date")
        if error:
            return error_response(error, 400)
        query = query.filter(Expense.expense_date <= parsed_to_date)

    if from_date is not None and to_date is not None:
        if parsed_from_date > parsed_to_date:
            return error_response("from_date must be on or before to_date.", 400)

    page, error = parse_positive_integer(request.args.get("page", "1"), "page")
    if error:
        return error_response(error, 400)
    limit, error = parse_positive_integer(
        request.args.get("limit", "10"), "limit", maximum=100
    )
    if error:
        return error_response(error, 400)

    pagination = query.order_by(Expense.expense_date.desc(), Expense.id.desc()).paginate(
        page=page, per_page=limit, error_out=False
    )
    return jsonify(
        expenses=[_expense_json(expense) for expense in pagination.items],
        pagination={
            "page": pagination.page,
            "limit": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
        },
    ), 200
