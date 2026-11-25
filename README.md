# Chess Tactics Trainer

A small FastAPI application for uploading chess board images/PDFs, recognizing a position locally with ChessTal, editing it on an interactive board, and saving confirmed positions as FEN in SQLite.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. Uploads are processed in memory and are not written to disk. ChessTal runs locally; its CNN dependencies, including TensorFlow and OpenCV, may take time and disk space to install. Positions are stored in `positions.sqlite3`; set `CHESS_DB_PATH` to change the database location.

## Recognition status

Recognition uses the open-source ChessTal CNN and board slicer. The first page of a PDF or uploaded image is processed in memory. The resulting board is editable; review it before saving because recognition can misclassify pieces. Side to move and castling rights cannot be inferred from a static diagram, so they default to white to move and no castling rights. Uploaded files and recognition debug crops are not stored.
