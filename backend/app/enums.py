import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    operator_record = "operator_record"
    operator_verify = "operator_verify"
