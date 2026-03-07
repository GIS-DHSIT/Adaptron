from adaptron.evaluate.domain import DomainEvaluator


def test_exact_match_scoring():
    evaluator = DomainEvaluator()
    predictions = ["Paris", "blue", "42"]
    references = ["Paris", "red", "42"]
    score = evaluator.exact_match(predictions, references)
    assert abs(score - 2 / 3) < 0.01


def test_eval_report_structure():
    evaluator = DomainEvaluator()
    report = evaluator.evaluate(
        predictions=["Paris", "42"], references=["Paris", "42"]
    )
    assert "exact_match" in report
    assert "total_samples" in report
    assert report["exact_match"] == 1.0
