from django.core.management.base import BaseCommand
from django.contrib.auth import authenticate
from getpass import getpass
from django.conf import settings

class Command(BaseCommand):
    help = 'CLI Login'

    def handle(self, *args, **kwargs):
        email = input('Email: ')
        password = getpass('Password: ')
        user = authenticate(username=email, password=password)
        if user:
            self.stdout.write('Logged in')
        else:
            self.stdout.write('Failed')