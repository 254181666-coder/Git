# Positioning

This directory will contain coordinate calculation and filtering logic.

First algorithm target:

- Use 3 or 4 anchor coordinates.
- Use tag-to-anchor distances.
- Calculate `x, y` with trilateration or least squares.
- Add simple smoothing after raw coordinates work.

Keep raw distance samples so algorithm changes can be replayed.

