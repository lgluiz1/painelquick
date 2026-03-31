import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from attendance.models import Company, Meeting, Course, Complaint, ComplaintCategory, UrgencyLevel

def migrate_to_saas():
    # 1. Create Default Company
    quick, created = Company.objects.get_or_create(
        name="Quick Delivery",
        slug="quick",
        defaults={
            'logo_url': 'https://quickdelivery.com.br/wp-content/uploads/2025/09/logo-quick-delivery-solucoes-em-logistica.webp',
            'primary_color': '#e63946'
        }
    )
    
    if created:
        print("Company 'Quick Delivery' created.")

    # 2. Assign existing records
    models_to_fix = [Meeting, Course, Complaint, ComplaintCategory, UrgencyLevel]
    for model in models_to_fix:
        count = model.objects.filter(company__isnull=True).update(company=quick)
        print(f"Updated {count} records for {model.__name__}")

if __name__ == "__main__":
    migrate_to_saas()
