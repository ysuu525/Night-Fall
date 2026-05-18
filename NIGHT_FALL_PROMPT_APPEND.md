# Night Fall prompt append

Keep Ombre Brain's normal startup flow.

After the ordinary `breath()` startup check, call:

```text
night_fall(action="surface")
```

Use `night_fall(action="generate")` only when the user explicitly asks to trigger Night Fall, or when your broader routine calls for a nightly dream-generation pass.

Do not replace Ombre's original `dream()` behavior. `dream()` remains Ombre's own tool; `night_fall` is a separate latent dream mechanism.
