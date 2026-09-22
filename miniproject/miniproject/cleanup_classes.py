import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'miniproject.settings')
django.setup()

from miniproject.scheduler.models import Class

# List the exact names the user wants
target_names = [
    "S6/S5CSA", "S6/S5CSB", "S4/S3CSA", "S4/S3CSB", "S8/S7CSA", "S8/S7CSB"
]

# Delete any classes that are NOT in the user's specific list
print("Removing old/mismatched class names...")
Class.objects.exclude(class_name__in=target_names).delete()

print("\nSuccess! Final Class List:")
for c in Class.objects.all():
    print(f"- {c.class_name} (Sem {c.semester})")
