#!/data/data/com.termux/files/usr/bin/bash

PROJECT="$HOME/storage/shared/Kaivor"
OUTPUT="$HOME/storage/downloads/Kaivor-latest.zip"

echo "Creating Kaivor snapshot..."

cd "$PROJECT" || exit 1

rm -f "$OUTPUT"

zip -r "$OUTPUT" . \
    -x "*/__pycache__/*" \
    -x "*.pyc" \
    -x "*.pyo" \
    -x ".git/*"

echo ""
echo "Done!"
echo "Saved to:"
echo "$OUTPUT"
