# Simple Calculator implementation used as repository template

# For Milestone F scaffolding, we include working implementations so tests pass
# deterministically. Later milestones can switch these to stubs to require edits.

def add(a, b):
    """Return the sum of two numbers."""
    return a + b


def multiply(a, b):
    """Return the product of two numbers."""
    return a * b


class Calculator:
    def add(self, a, b):
        return add(a, b)

    def multiply(self, a, b):
        return multiply(a, b)

