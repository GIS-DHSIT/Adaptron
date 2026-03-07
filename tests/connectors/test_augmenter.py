from adaptron.connectors.augmenter import DataAugmenter, AugmentConfig


def test_synonym_swap():
    augmenter = DataAugmenter()
    dataset = [{"instruction": "Explain machine learning", "response": "ML is..."}]
    result = augmenter.augment(dataset, AugmentConfig(synonym_swap=True, target_multiplier=2.0))
    assert len(result) >= 2  # original + augmented


def test_preserve_originals():
    augmenter = DataAugmenter()
    dataset = [{"instruction": "Hello", "response": "Hi"}]
    result = augmenter.augment(dataset, AugmentConfig(synonym_swap=True, preserve_originals=True))
    assert dataset[0] in result


def test_no_augmentation_returns_original():
    augmenter = DataAugmenter()
    dataset = [{"instruction": "Test", "response": "OK"}]
    result = augmenter.augment(dataset, AugmentConfig())
    assert result == dataset
