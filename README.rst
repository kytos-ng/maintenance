Overview
========

**WARNING: As previously announced on our communication channels, the Kytos
project will enter the "shutdown" phase on May 31, 2021. After this date,
only critical patches (security and core bug fixes) will be accepted, and the
project will be in "critical-only" mode for another six months (until November
30, 2021). For more information visit the FAQ at <https://kytos.io/faq>. We'll
have eternal gratitude to the entire community of developers and users that made
the project so far.**

This NApp creates maintenance windows, allowing the maintenance of network
devices (a switch, a board, a link) without receiving alerts. The circuits
using those devices will be moved to another path during the maintenance, if
possible. Notifications about those devices will be disabled during the
maintenance.

Requirements
============
This NApp requires the `apscheduler` python package to schedule the
maintenances.
