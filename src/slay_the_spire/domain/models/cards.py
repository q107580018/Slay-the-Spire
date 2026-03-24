from __future__ import annotations


def card_id_from_instance_id(card_instance_id: str) -> str:
    if not isinstance(card_instance_id, str):
        raise TypeError("card_instance_id must be a string")
    if not card_instance_id:
        raise ValueError("card_instance_id must not be empty")

    separators = ("#", ":", "-")
    for separator in separators:
        if separator in card_instance_id:
            card_id = card_instance_id.split(separator, 1)[0]
            if card_id:
                return card_id

    return card_instance_id
