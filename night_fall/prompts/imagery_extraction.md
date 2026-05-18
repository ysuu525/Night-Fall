Extract concrete dream imagery from selected Ombre memory buckets.

Your job is to find small image-bearing fragments that can enter a dream.
Prefer concrete, sensory, spatial, object-like, bodily, or emotionally charged phrases.
Avoid abstract summary, theme labels, interpretation, explanation, and invented metaphor.
Do not compress a whole memory into a recap.

Return only JSON:

```json
{
  "imagery_fragments": [
    {
      "source_bucket_id": "bucket id",
      "excerpt": "exact excerpt copied from the source content"
    }
  ]
}
```

Rules:
- Return 3 to 6 fragments when possible.
- Each excerpt should be short, roughly 4 to 30 Chinese characters or a similar English phrase length.
- One bucket may contribute 0 to 2 fragments.
- The excerpt must be copied from the source content, or be a very close trimmed span that can be located in the source content.
- Do not explain why you chose a fragment.
- Do not generate new imagery that is not already in the source.
