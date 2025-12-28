from rest_framework.throttling import UserRateThrottle

class RegistrationRateThrottle(UserRateThrottle):
    scope = 'registration'

class ActivationRateThrottle(UserRateThrottle):
    scope = 'activation'

class LoginRateThrottle(UserRateThrottle):
    scope = 'login'

class ChangePasswordRateThrottle(UserRateThrottle):
    scope = 'change_password'

class ProfileRateThrottle(UserRateThrottle):
    scope = 'profile'