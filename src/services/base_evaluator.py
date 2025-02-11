class BaseEvaluator:
    def evaluate(
        self, question_text: str, claim: str, argument: str, counterargument: str
    ):
        raise NotImplementedError("Subclasses must implement the evaluate method")
