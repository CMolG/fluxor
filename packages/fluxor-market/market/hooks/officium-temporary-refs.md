# officium-temporary-refs: No Temporary References at Review

The check that refuses a card's move to review is not running in this client, so run it yourself.
Before you move a card to review, run the backlog skill's `scripts/card_refs.py list <KEY>`. Every
`card://<KEY> [temporary]` reference it lists is resolved in this card, or re-pointed to a follow-up
card (`card://<OTHER> [temporary]`) that says when it goes. Only then move the card.
