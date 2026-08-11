"""MCP tool: create a new object in the running FreeCAD (text + optional screenshot)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class CreateObjectArgs(BaseModel):
    doc_name: str = Field(description="The name of the document to create the object in.")
    obj_type: str = Field(
        description=(
            "The type of the object to create (e.g. 'Part::Box', 'Part::Cylinder', "
            "'Draft::Circle', 'PartDesign::Body', etc.)."
        )
    )
    obj_name: str = Field(description="The name of the object to create.")
    analysis_name: Optional[str] = Field(
        default=None, description="The name of the FEM analysis to add the object to (for Fem:: objects)."
    )
    obj_properties: Optional[dict] = Field(default=None, description="The properties of the object to create.")


TOOL: dict[str, Any] = {
    "name": "create_object",
    "description": (
        "Create a new object in FreeCAD.\n"
        'Object type starts with "Part::" or "Draft::" or "PartDesign::" or "Fem::".\n\n'
        "Args:\n"
        "    doc_name: The name of the document to create the object in.\n"
        "    obj_type: The type of the object to create (e.g. 'Part::Box', 'Part::Cylinder', "
        "'Draft::Circle', 'PartDesign::Body', etc.).\n"
        "    obj_name: The name of the object to create.\n"
        "    obj_properties: The properties of the object to create.\n\n"
        "Returns:\n"
        "    A message indicating the success or failure of the object creation and a screenshot of the object.\n\n"
        "Examples:\n"
        "    If you want to create a cylinder with a height of 30 and a radius of 10, you can use the following data.\n"
        "    ```json\n"
        "    {\n"
        '        "doc_name": "MyCylinder",\n'
        '        "obj_name": "Cylinder",\n'
        '        "obj_type": "Part::Cylinder",\n'
        '        "obj_properties": {\n'
        '            "Height": 30,\n'
        '            "Radius": 10,\n'
        '            "Placement": {\n'
        '                "Base": {\n'
        '                    "x": 10,\n'
        '                    "y": 10,\n'
        '                    "z": 0\n'
        "                },\n"
        '                "Rotation": {\n'
        '                    "Axis": {\n'
        '                        "x": 0,\n'
        '                        "y": 0,\n'
        '                        "z": 1\n'
        "                    },\n"
        '                    "Angle": 45\n'
        "                }\n"
        "            },\n"
        '            "ViewObject": {\n'
        '                "ShapeColor": [0.5, 0.5, 0.5, 1.0]\n'
        "            }\n"
        "        }\n"
        "    }\n"
        "    ```\n\n"
        "    If you want to create a circle with a radius of 10, you can use the following data.\n"
        "    ```json\n"
        "    {\n"
        '        "doc_name": "MyCircle",\n'
        '        "obj_name": "Circle",\n'
        '        "obj_type": "Draft::Circle",\n'
        "    }\n"
        "    ```\n\n"
        "    If you want to create a FEM analysis, you can use the following data.\n"
        "    ```json\n"
        "    {\n"
        '        "doc_name": "MyFEMAnalysis",\n'
        '        "obj_name": "FemAnalysis",\n'
        '        "obj_type": "Fem::AnalysisPython",\n'
        "    }\n"
        "    ```\n\n"
        "    If you want to create a FEM constraint, you can use the following data.\n"
        "    ```json\n"
        "    {\n"
        '        "doc_name": "MyFEMConstraint",\n'
        '        "obj_name": "FemConstraint",\n'
        '        "obj_type": "Fem::ConstraintFixed",\n'
        '        "analysis_name": "MyFEMAnalysis",\n'
        '        "obj_properties": {\n'
        '            "References": [\n'
        "                {\n"
        '                    "object_name": "MyObject",\n'
        '                    "face": "Face1"\n'
        "                }\n"
        "            ]\n"
        "        }\n"
        "    }\n"
        "    ```\n\n"
        "    If you want to create a FEM mechanical material, you can use the following data.\n"
        "    ```json\n"
        "    {\n"
        '        "doc_name": "MyFEMAnalysis",\n'
        '        "obj_name": "FemMechanicalMaterial",\n'
        '        "obj_type": "Fem::MaterialCommon",\n'
        '        "analysis_name": "MyFEMAnalysis",\n'
        '        "obj_properties": {\n'
        '            "Material": {\n'
        '                "Name": "MyMaterial",\n'
        '                "Density": "7900 kg/m^3",\n'
        '                "YoungModulus": "210 GPa",\n'
        '                "PoissonRatio": 0.3\n'
        "            }\n"
        "        }\n"
        "    }\n"
        "    ```\n\n"
        "    If you want to create a FEM mesh, you can use the following data.\n"
        "    The `Shape` property is required (legacy `Part` is also accepted).\n"
        "    On FreeCAD 1.x the size limits are `CharacteristicLengthMax/Min`;\n"
        "    the legacy `ElementSizeMax/Min` keys are also accepted.\n"
        "    ```json\n"
        "    {\n"
        '        "doc_name": "MyFEMMesh",\n'
        '        "obj_name": "FemMesh",\n'
        '        "obj_type": "Fem::FemMeshGmsh",\n'
        '        "analysis_name": "MyFEMAnalysis",\n'
        '        "obj_properties": {\n'
        '            "Shape": "MyObject",\n'
        '            "CharacteristicLengthMax": 10,\n'
        '            "CharacteristicLengthMin": 0.1\n'
        "        }\n"
        "    }\n"
        "    ```"
    ),
    "args": CreateObjectArgs,
}


def handle(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    from freeglm_freecad._responses import add_screenshot_if_available, text_response
    from freeglm_freecad.loader import get_connection, only_text_feedback

    doc_name = arguments.get("doc_name")
    obj_type = arguments.get("obj_type")
    obj_name = arguments.get("obj_name")
    analysis_name = arguments.get("analysis_name")
    obj_properties = arguments.get("obj_properties")
    only_text = only_text_feedback()
    try:
        conn = get_connection()
        obj_data = {
            "Name": obj_name,
            "Type": obj_type,
            "Properties": obj_properties or {},
            "Analysis": analysis_name,
        }
        res = conn.create_object(doc_name, obj_data)
        if res.get("success"):
            response = text_response(f"Object '{res['object_name']}' created successfully")
        else:
            return text_response(f"Failed to create object: {res.get('error')}")
        screenshot = None if only_text else conn.get_active_screenshot()
        return add_screenshot_if_available(response, screenshot, only_text)
    except Exception as e:
        return text_response(f"Failed to create object: {e}")
