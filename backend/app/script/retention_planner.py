# ruff: noqa: E501
"""Non-factual retention prompts that do not manufacture suspense."""


def retention_devices() -> list[dict[str, str]]:
    return [
        {
            "stage": "Opening",
            "device": "State the evidence question and delay only the qualified conclusion.",
        },
        {
            "stage": "Middle",
            "device": "Contrast what an artifact supports with what it cannot establish.",
        },
        {
            "stage": "Ending",
            "device": "Return to the opening question and give the best-supported answer.",
        },
    ]
