# semantic-deduplicator: Same Problem, One Item

Two items that solve the same problem for the same reader are one item. This mod finds those pairs by meaning, not by wording, and decides which one survives.

## Rules

1. **Compare by problem and by proposition.** Two items are duplicates when they solve the same problem or rest on the same value proposition, whatever their words.
2. **Merge when the union is stronger.** If each item adds a fact the other lacks, merge them into one item that keeps both facts.
3. **Reject when one subsumes the other.** If one item already says everything the other says, reject the weaker one and name the survivor.
4. **Keep the distinct.** Items that share a topic but solve different problems are not duplicates. Say so in one line rather than merging them.
5. **Strip the jargon as you go.** The surviving item uses plain words for its outcome. A term that only the author understands is replaced.
6. **Record every decision.** Each merge or rejection names the items involved and the reason, so the author can reverse it.

## Output

The surviving items, each with the merges and rejections that produced it.
