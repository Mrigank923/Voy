from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AnonOTPThrottle(AnonRateThrottle):
    rate = "10/hour"


class AnonVerificationThrottle(AnonRateThrottle):
    rate = "10/hour"


class UserOTPThrottle(UserRateThrottle):
    rate = "20/hour"


class UserVerificationThrottle(UserRateThrottle):
    rate = "20/hour"
