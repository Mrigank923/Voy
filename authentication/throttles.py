from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AnonOTPThrottle(AnonRateThrottle):
    rate = "100/hour"


class AnonVerificationThrottle(AnonRateThrottle):
    rate = "100/hour"


class UserOTPThrottle(UserRateThrottle):
    rate = "200/hour"


class UserVerificationThrottle(UserRateThrottle):
    rate = "200/hour"
