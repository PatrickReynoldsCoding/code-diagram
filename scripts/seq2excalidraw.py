"""Turn a sequence spec (JSON) into an .excalidraw file whose shapes link to code via idea://.

Usage: python3 seq2excalidraw.py <spec.json> <out.excalidraw>
"""
import json
import random
import sys
from urllib.parse import quote

from pydantic import BaseModel, Field

BOX_WIDTH, BOX_HEIGHT, GAP_X, TOP_Y, STEP_Y = 220, 60, 120, 80, 70
SELF_LOOP_WIDTH = 60
PARTICIPANT_COLOUR = "#a5d8ff"
LIFELINE_COLOUR = "#868e96"


class Participant(BaseModel):
    id: str
    label: str
    file: str | None = None
    line: int | None = None


class Message(BaseModel):
    from_: str = Field(alias="from")
    to: str
    label: str
    file: str | None = None
    line: int | None = None
    is_return: bool = Field(default=False, alias="return")


class SequenceSpec(BaseModel):
    title: str | None = None
    participants: list[Participant]
    messages: list[Message]


def _idea_link(file: str | None, line: int | None) -> str | None:
    if not file:
        return None
    return f"idea://open?file={quote(file)}&line={line or 1}"


def _base_element(kind: str, element_id: str, x: float, y: float, width: float, height: float, **extra) -> dict:
    return {
        "type": kind, "id": element_id, "x": x, "y": y, "width": width, "height": height, "angle": 0,
        "strokeColor": "#1e1e1e", "backgroundColor": "transparent", "fillStyle": "solid",
        "strokeWidth": 2, "strokeStyle": "solid", "roughness": 0, "opacity": 100,
        "groupIds": [], "frameId": None, "roundness": None, "seed": random.randint(1, 2**31),
        "version": 1, "versionNonce": random.randint(1, 2**31), "isDeleted": False,
        "boundElements": [], "updated": 1, "link": None, "locked": False, **extra,
    }


def _text_element(element_id: str, x: float, y: float, width: float, height: float, value: str,
                  container_id: str | None = None, link: str | None = None, font_size: int = 16,
                  align: str = "center") -> dict:
    return _base_element("text", element_id, x, y, width, height, text=value, originalText=value,
                         fontSize=font_size, fontFamily=2, textAlign=align, verticalAlign="middle",
                         containerId=container_id, autoResize=True, lineHeight=1.25, link=link)


def _participant_elements(participant: Participant, column: int, bottom_y: float) -> tuple[list[dict], float]:
    left_x = column * (BOX_WIDTH + GAP_X)
    centre_x = left_x + BOX_WIDTH / 2
    link = _idea_link(participant.file, participant.line)
    box_id = f"p-{participant.id}"
    label_id = f"{box_id}-t"
    box = _base_element("rectangle", box_id, left_x, TOP_Y, BOX_WIDTH, BOX_HEIGHT,
                        backgroundColor=PARTICIPANT_COLOUR, roundness={"type": 3}, link=link,
                        boundElements=[{"type": "text", "id": label_id}])
    label = _text_element(label_id, left_x + 10, TOP_Y + 18, BOX_WIDTH - 20, 24, participant.label,
                          container_id=box_id, link=link)
    lifeline_length = bottom_y - TOP_Y - BOX_HEIGHT
    lifeline = _base_element("line", f"l-{participant.id}", centre_x, TOP_Y + BOX_HEIGHT, 0, lifeline_length,
                             strokeStyle="dashed", strokeColor=LIFELINE_COLOUR,
                             points=[[0, 0], [0, lifeline_length]])
    return [box, label, lifeline], centre_x


def _arrow_points(start_x: float, end_x: float) -> list[list[float]]:
    # A call to itself has no horizontal length, so draw it as a small loop to the right.
    if start_x == end_x:
        return [[0, 0], [SELF_LOOP_WIDTH, 0], [SELF_LOOP_WIDTH, STEP_Y / 2], [0, STEP_Y / 2]]
    return [[0, 0], [end_x - start_x, 0]]


def _message_elements(message: Message, step: int, centre_x_by_id: dict[str, float]) -> list[dict]:
    start_x = centre_x_by_id[message.from_]
    end_x = centre_x_by_id[message.to]
    arrow_y = TOP_Y + BOX_HEIGHT + 40 + step * STEP_Y
    points = _arrow_points(start_x, end_x)
    width = max(abs(point[0]) for point in points)
    link = _idea_link(message.file, message.line)
    arrow_id = f"m-{step}"
    label_id = f"{arrow_id}-t"
    arrow = _base_element("arrow", arrow_id, start_x, arrow_y, width, points[-1][1],
                          points=points, strokeStyle="dashed" if message.is_return else "solid",
                          startArrowhead=None, endArrowhead="arrow", startBinding=None, endBinding=None,
                          elbowed=False, link=link, boundElements=[{"type": "text", "id": label_id}])
    label = _text_element(label_id, min(start_x, end_x), arrow_y - 22, max(abs(end_x - start_x), 200), 20,
                          f"{step + 1}. {message.label}", container_id=arrow_id, link=link, font_size=14)
    return [arrow, label]


def build_excalidraw(spec: SequenceSpec) -> dict:
    bottom_y = TOP_Y + BOX_HEIGHT + 40 + len(spec.messages) * STEP_Y
    elements: list[dict] = []
    if spec.title:
        elements.append(_text_element("title", 0, 10, 900, 30, spec.title, font_size=24, align="left"))
    centre_x_by_id: dict[str, float] = {}
    for column, participant in enumerate(spec.participants):
        participant_elements, centre_x = _participant_elements(participant, column, bottom_y)
        elements += participant_elements
        centre_x_by_id[participant.id] = centre_x
    for step, message in enumerate(spec.messages):
        elements += _message_elements(message, step, centre_x_by_id)
    return {"type": "excalidraw", "version": 2, "source": "claude-code-diagram",
            "elements": elements, "appState": {"viewBackgroundColor": "#ffffff"}, "files": {}}


def main(spec_path: str, output_path: str) -> None:
    with open(spec_path) as spec_file:
        spec = SequenceSpec.model_validate(json.load(spec_file))
    with open(output_path, "w") as output_file:
        json.dump(build_excalidraw(spec), output_file, indent=2)
    print(f"Wrote {output_path} ({len(spec.participants)} participants, {len(spec.messages)} messages)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
