# Do not copy this into subscription/migrations/ without reading this first

This migration deletes 7 existing database tables (Coupon, Payment, Refund,
SubscriptionPackage, SubscriptionHistory, SubscriptionAnalytics, UsageTracking,
Notification, PaymentPlan) and replaces them with newer models the code has
already moved to (SubscriptionPlanTier, SubscriptionPlanPrice,
PlanExamAccessLimit, UserExamAccess).

Before applying this anywhere with real data:

1. Back up the database.
2. Check whether the old tables have any rows:
   SELECT COUNT(*) FROM subscription_payment;
   SELECT COUNT(*) FROM subscription_subscriptionhistory;
   SELECT COUNT(*) FROM subscription_subscriptionpackage;
   (and so on for the others listed above)
3. If they're empty, this migration is safe to apply as-is.
4. If they have data, you need a plan to migrate that data into the new
   model shape BEFORE running this migration - it does not do that for you,
   it just drops the old tables.

To apply once you've confirmed it's safe:
  cp 0005_planexamaccesslimit_subscriptionplanprice_and_more.py ../subscription/migrations/
  python3 manage.py migrate subscription
