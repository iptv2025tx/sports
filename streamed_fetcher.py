name: Update M3U Playlist

on:
  schedule:
    # Runs every hour on the hour (UTC)
    - cron: '0 * * * *'
  workflow_dispatch: # Allows you to run it manually from the Actions tab

jobs:
  update-playlist:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests

      - name: Run Stream Fetcher
        run: python streamed_fetcher.py

      - name: Commit and push changes
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git add streamed.m3u
          git commit -m "Automated update of streamed.m3u" || echo "No changes to commit"
          git push
