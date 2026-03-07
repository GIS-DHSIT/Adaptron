"""Data augmenter for training data preprocessing."""

from __future__ import annotations

import copy
import logging
import random
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Built-in synonym dictionary for simple swap augmentation
_SYNONYMS: dict[str, list[str]] = {
    "good": ["great", "excellent", "fine"],
    "great": ["good", "excellent", "wonderful"],
    "explain": ["describe", "elaborate", "clarify"],
    "describe": ["explain", "illustrate", "depict"],
    "fast": ["quick", "rapid", "swift"],
    "quick": ["fast", "rapid", "speedy"],
    "big": ["large", "huge", "enormous"],
    "large": ["big", "huge", "vast"],
    "small": ["tiny", "little", "compact"],
    "important": ["significant", "crucial", "vital"],
    "simple": ["easy", "basic", "straightforward"],
    "hard": ["difficult", "tough", "challenging"],
    "show": ["display", "present", "demonstrate"],
    "make": ["create", "build", "produce"],
    "use": ["utilize", "employ", "apply"],
    "help": ["assist", "aid", "support"],
}


@dataclass
class AugmentConfig:
    paraphrase: bool = False
    paraphrase_model: str | None = None
    synonym_swap: bool = False
    back_translate: bool = False
    balance_categories: bool = False
    target_multiplier: float = 2.0
    preserve_originals: bool = True


class DataAugmenter:
    """Augments training datasets with various strategies."""

    def augment(self, dataset: list[dict], config: AugmentConfig | None = None) -> list[dict]:
        if config is None:
            config = AugmentConfig()

        result: list[dict] = []

        if config.preserve_originals:
            result.extend(dataset)

        augmented: list[dict] = []

        if config.paraphrase:
            logger.warning("Paraphrase augmentation requires an external model")

        if config.back_translate:
            logger.warning("Back-translation augmentation requires an external model")

        if config.synonym_swap:
            target_total = int(len(dataset) * config.target_multiplier)
            needed = target_total - len(result)
            while len(augmented) < needed:
                for item in dataset:
                    if len(augmented) >= needed:
                        break
                    new_item = self._synonym_swap(item)
                    augmented.append(new_item)

        if config.balance_categories:
            augmented.extend(self._balance_categories(dataset, config.target_multiplier))

        result.extend(augmented)

        # If nothing was enabled, just return original dataset
        if not result:
            return list(dataset)

        return result

    @staticmethod
    def _synonym_swap(item: dict) -> dict:
        new_item = copy.deepcopy(item)
        for key, value in new_item.items():
            if isinstance(value, str):
                words = value.split()
                new_words = []
                for word in words:
                    lower = word.lower()
                    if lower in _SYNONYMS:
                        replacement = random.choice(_SYNONYMS[lower])
                        # Preserve original casing (first letter)
                        if word[0].isupper():
                            replacement = replacement.capitalize()
                        new_words.append(replacement)
                    else:
                        new_words.append(word)
                new_item[key] = " ".join(new_words)
        return new_item

    @staticmethod
    def _balance_categories(dataset: list[dict], target_multiplier: float) -> list[dict]:
        from collections import Counter

        categorized = [item for item in dataset if "category" in item]
        if not categorized:
            return []

        counts = Counter(item["category"] for item in categorized)
        max_count = int(max(counts.values()) * target_multiplier)

        augmented: list[dict] = []
        by_category: dict[str, list[dict]] = {}
        for item in categorized:
            by_category.setdefault(item["category"], []).append(item)

        for cat, items in by_category.items():
            needed = max_count - counts[cat]
            for i in range(needed):
                augmented.append(copy.deepcopy(items[i % len(items)]))

        return augmented
