from __future__ import annotations

import io
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Annotated, Literal

import chess
import fitz
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("CHESS_DB_PATH", ROOT / "positions.sqlite3"))
app = FastAPI(title="Chess Position Scanner")
app.mount("/static", StaticFiles(directory=ROOT / "app/static"), name="static")


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


with connect() as db:
    db.execute("""CREATE TABLE IF NOT EXISTS positions (
        id TEXT PRIMARY KEY, fen TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")


@app.get("/")
def home():
    return FileResponse(ROOT / "app/templates/index.html")


def image_from_upload(data: bytes, filename: str) -> Image.Image:
    if filename.lower().endswith(".pdf"):
        try:
            doc = fitz.open(stream=data, filetype="pdf")
            if not doc.page_count:
                raise ValueError("PDF has no pages")
            pix = doc[0].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            return Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        except Exception as exc:
            raise HTTPException(400, f"Could not read PDF: {exc}") from exc
    try:
        return Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as exc:
        raise HTTPException(400, "Could not read image. Use PNG or JPG.") from exc


ImageCorner = Literal["a8", "a1", "h1"]
DEFAULT_TOP_LEFT: ImageCorner = "a1"


def detect_position(
    image: Image.Image, top_left: ImageCorner = DEFAULT_TOP_LEFT
) -> tuple[str, float]:
    """Run ChessTal on the in-memory image; disable all debug output to avoid saving uploads."""
    try:
        import cv2
        import numpy as np
        from chesstal import BoardSlicer, PieceRecognizer
    except ImportError as exc:
        raise HTTPException(
            503,
            "Recognition dependencies are missing. Install requirements.txt and restart the app.",
        ) from exc

    # ChessTal accepts an OpenCV BGR array. Passing no output directory prevents it
    # from writing cropped squares or debug images to disk.
    rgb = np.asarray(image.convert("RGB"))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    try:
        squares = BoardSlicer(output_dir=None, debug=False).slice_board_from_image(bgr)
        pieces = PieceRecognizer().classify_board(squares)
    except FileNotFoundError as exc:
        raise HTTPException(503, "The ChessTal recognition model is not installed correctly.") from exc
    except Exception as exc:
        raise HTTPException(422, f"Could not recognize a chessboard in this file: {exc}") from exc

    board = chess.Board(None)
    for square_name, piece in pieces.items():
        if len(piece) != 1 or piece not in "PNBRQKpnbrqk":
            continue
        square = chess.parse_square(square_name)
        # ChessTal labels the top-left tile a8 regardless of the source.
        if top_left == "a1":
            square = chess.square_mirror(square)
        elif top_left == "h1":
            square = chess.H8 - square
        board.set_piece_at(square, chess.Piece.from_symbol(piece))
    return board.fen(), 0.0


@app.post("/api/recognize")
async def recognize(
    file: UploadFile = File(...),
    top_left: Annotated[ImageCorner, Form()] = DEFAULT_TOP_LEFT,
):
    filename = file.filename or ""
    if not filename.lower().endswith((".pdf", ".png", ".jpg", ".jpeg")):
        raise HTTPException(415, "Upload a PDF, PNG, or JPG file.")
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "File is too large (maximum 15 MB).")
    image = image_from_upload(data, filename)
    fen, confidence = detect_position(image, top_left)
    return {"fen": fen, "confidence": confidence, "message": "Recognition complete. Review the position and correct any pieces before saving."}


class Position(BaseModel):
    fen: str


@app.post("/api/positions")
def save_position(position: Position):
    try:
        board = chess.Board(position.fen)
    except ValueError as exc:
        raise HTTPException(400, f"Invalid FEN: {exc}") from exc
    position_id = str(uuid.uuid4())
    with connect() as db:
        db.execute("INSERT INTO positions (id, fen) VALUES (?, ?)", (position_id, board.fen()))
    return {"id": position_id, "fen": board.fen()}


@app.get("/api/positions")
def list_positions():
    with connect() as db:
        rows = db.execute("SELECT id, fen, created_at FROM positions ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]
