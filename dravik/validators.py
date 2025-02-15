from datetime import date

from textual.validation import Validator, ValidationResult


class Date(Validator):
    def validate(self, value: str = "") -> ValidationResult:
        if not value:
            return self.success()

        try:
            date(*[int(p) for p in value.split("-") if p])
        except (TypeError, ValueError):
            return self.failure("Not a valid date!")
        return self.success()
