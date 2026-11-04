
from backend.services.ai_service import generate_part_description

description = generate_part_description(
    part_name="Industrial Water Pump",
    category="Mechanical Equipment",
    manufacturer="ABC Industries"
)

print("\nGenerated Part Description:\n")
print(description)
