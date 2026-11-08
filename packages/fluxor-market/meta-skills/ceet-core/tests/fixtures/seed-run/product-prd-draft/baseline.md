# PRD: Admin 2FA

## Overview

We will add two-factor authentication to the admin login. This will
make admin accounts more secure.

## Scope

- Admin login flow gets a 2FA step.
- Recovery flow for users who lose their device.

## Out of scope

- Mobile.
- Customer (non-admin) accounts.

## Success metrics

- Number of admin accounts with 2FA enabled.
- Reduction in security incidents.

## Rollout

- Internal testing first.
- Then roll out to all admins.
- Mandatory after a grace period.

## Risks

- Some admins may not enroll.
- Some admins may lose access if recovery is not handled well.

## Conclusion

This addresses the SOC2 finding and reduces risk. Estimated 3 weeks
with 2 backend + 1 frontend engineer.
