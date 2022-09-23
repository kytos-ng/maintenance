
:EP: 001
:Title: Maintenance Window for items on the network
:Authors: - Jeronimo Bezerra jbezerra@fiu.edu;
          - Arturo Quintana arquinta@fiu.edu ;
          - Italo Valcy idasilva@fiu.edu
         
:Issued Date: to be defined
:Status: Draft
:Type: Standards Track


########
Abstract
########

This blueprint details the main features, workflows and requirements for a Network Team operate and orchestrate the backbone specially related to Maintenance Window on an item of the network. Thus any application that implement the orchestration of a Network should follow this specification to provide a Maintenance Mode feature.

##########
Motivation
##########

When a Network Operator is going to plan, program and execute the maintenance operations there are some activities that needs to be accomplished  before, during and after the Maintenance Window. The Network Orchestration Tool should provide features to help the Network Operator on those activities, such as:

- Disable user notifications: it's common have service oscillation or flapping during the MW (e.g. links going up and down, switch reboot, ports up/down) and the user (Customer, Partner or Operator) dont want to be flooded of notifications during the MW (i.e. no e-mails, no sms, no media alerts)

- List of services/users affected by the MW: it's important have a clear view of who is going to be affected by the MW before it is even scheduled, so the Operator can send notifications to its customers/partner  in advance.

- Move services away from items under MW: from the orchestration perspective it's essential to move all possible production services away from the item under MW, so the customer/partner has no outage. Furthermore, it may be interesting not allow Customer/Partner users to request new services that rely on items under MW. Any change/movement of services on the network due to items under MW should respect user requirements

- Test Plan: well-planned MW has a Test Plan to ensure that deployed changes meet service healthy and customer expectations. From the Network Orchestration perspective, it's important having ways to test the items under MW to ensure they are working properly. Thus the Operator may request the creation of services using the items under MW just to run his/her Test Plan.


#############
Specification
#############

1. Admin request a MW on a LINK, UNI or SWITCH for a specific period of time
2. The orchestration tool  should disable user notifications for the provided item
3. When the MW begins, the orchestration tool should run a set of steps as detailed bellow:

3.1. For a Link: take all the Services that uses the link under MW as part of the path (either primary or backup)  and apply the following table on each of them:

+------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+-----------------------------------------------------------------------+
|                  | Dynamic Path                                                                                                                                                                                                                                | Static Path                                                           |
+------------------+-----------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+                                                                       |
|                  | No User requirements                                      | With User Requirements                                                                                                                                                          |                                                                       |
+------------------+-----------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+-----------------------------------------------------------------------+
| Has alternative  | 3.1.1) Find a new path                                    | 3.1.1) Find a new Path                                                                                                                                                          | Move the service to the alternative Route                             |
| route            |                                                           |                                                                                                                                                                                 | ** Pay attention to check if the MW affects                           |
|                  | 3.1.2) move the service to the new path When MW Ends: 5.A | 3.1.2) Move the service to the new path                                                                                                                                         | all static path (primary and backup)                                  |
|                  |                                                           |                                                                                                                                                                                 |                                                                       |
|                  |                                                           | When MW Ends: 5.A                                                                                                                                                               | When MW Ends: 5.C                                                     |
+------------------+-----------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+-----------------------------------+-----------------------------------+
| No alternative   | 3.1.1) ask for user confirmation                          | 3.1.1) No alternative Route that fulfils the User Requirements. So, check for the user provided configuration during provisioning about "open mind" or not to find a new path:  | User is not "open mind" or        | There is an alternative physical  |
|  route           |                                                           |                                                                                                                                                                                 | there is no alternative physical  | path and User is "open mind"      |
|                  | 3.1.2) disable service during the MW                      |                                                                                                                                                                                 | path                              |                                   |
|                  |                                                           | - if user is "open mind", then: i) find a new path; ii) move the circuit; iii) When MW                                                                                          |                                   | 3.1.1) Find a new path            |
|                  | When MW Ends: B                                           | Ends: C                                                                                                                                                                         | 3.1.1) ask for confirmation       |                                   |
|                  |                                                           |                                                                                                                                                                                 |                                   | 3.1.2) Move the service           |
|                  |                                                           | - if user is not "open mind", then: i) ask for confirmation; ii) disable the circuit; iii)                                                                                      |                                   |                                   |
|                  |                                                           | When MW Ends: B                                                                                                                                                                 | 3.1.2) disable the service        | When MW Ends: C                   |
|                  |                                                           |                                                                                                                                                                                 |                                   |                                   |
|                  |                                                           | 3.1.2) No Alternative Route because there is no PATH:                                                                                                                           |                                   |                                   |
|                  |                                                           | i) Ask confirmation; ii) disable service;                                                                                                                                       | When MW Ends: B                   |                                   |
|                  |                                                           | iii) When MW Ends: B                                                                                                                                                            |                                   |                                   |
+------------------+-----------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+-----------------------------------+-----------------------------------+

.. The table above was generated using https://www.tablesgenerator.com/text_tables  (see saved table on ./static/table/ep001-table1.tgn)

3.2. For a UNI: disable service during the MW and When MW ends: 5.B

3.3. For a Switch: 

3.3.1. take all the Services whose UNIs is at the switch and apply the same as step 3.2

3.3.2. take all the Services whose path (either primary or backup) pass through the switch under MW and apply the same logic as 3.1 (pay attention to remove all the links connected to the switch under MW before find a new path - i.e. not consider any link on the switch under MW as a alternative path)

4. Testing Phase: The Operator should be able to create services using the items under MW to make tests and validate the maintenance activities
5. When the MW ends, or when the Operator explictly ask for the end of MW, the orchestration tool should run a set of steps as detailed bellow:

- 5.A - Leave the service as it is currently 
- 5.B - Enable the service 
- 5.C - Restore the service AS IT WAS BEFORE the MW (i.e. should use the "saved setup" before the MW and no ask for path_finder to find path) 

Points of Attention (PA):

- PA1. It should be possible to generate a report of Services and Users that will be affected by a future MW. The report should take into consideration items under MW mode in primary or backup PATH. For instance, if the MW will affect LinkA but LinkA is a primary path for EVC 1 and the only backup path for EVC 2, then the report should issue a warning about EVC 1 and EVC 2. It should not be necessary to create a MW to accomplish this.
- PA2. Every Action should be logged and reported on the end of MW 
- PA3. The services available on the Orchestration Tool (e.g. MEF e-Line) should have an user configuration option to allow or not flexible backup path (a.k.a. open mind user), with the default value of allow flexible backup path.
- PA4. The orchestration tool should be able to support multiple MW at the same time (e.g. two links, many UNIs, etc)
- PA5. The orchestration tool should be able to support multiple items under MW in the same operation (e.g. a link, a switch and many UNIs).
- PA6. When scheduling a new MW, the orchestration tool should take into consideration other scheduled MWs and how the topology of the network is supposed to be at that time in order to verify alternative routes and affected services by that new MW. For example, the orchestration tool may picture the future network topology *without links under the MW already scheduled*  and, using that future topology, check how the new MW will affect services. Thus, if a sheduled MW will affect a Link A or a Switch X, that Link A or Switch X should not be considered as part of a alternative route for the new MW being scheduled. The same logic should be applied for a report of possible affected Users/Services.


##############
Rejected Ideas
##############

[Why certain ideas that were brought while discussing this PEP were not ultimately pursued.]


###########
Open Issues
###########

[Any points that are still being decided/discussed.]


########
Glossary
########

- Maintenance - Maintenance activities are focused on facilitating
  repairs and upgrades -- for example, when equipment must be
  replaced, when a router needs a patch for an operating system
  image, a link needs to be repaired, or a customer is going to
  make some change on its side. Maintenance also involves corrective 
  and preventive measures to make the managed network run more 
  effectively, e.g., adjusting device configuration and parameters [rfc6291].

- Maintenance Window (MW) - time slot between the start of the maintenance 
  and its end. Usually the Network Ops Team send a notification to all
  users/customers/partners affected by the MW and then the they are
  aware if the service will be available or not during that time slot.

- Item under MW - an item under MW is the network component/equipment
  that is going to be affected by the maintenance activities during 
  the time slot. Item under MW can be: UNI (User Network Interface), 
  Link or Switch.

- User requirements - Set of parameters required by the user when the 
  service was created: bandwidth, delay, localization (Atlantic, 
  Pacific, terrestrial / submarine), not shared with EVC XYZ, etc

- Fulfils user requirements - service provisioning is compliance 
  with user requirements

- Dynamic Path - the user requested a circuit and specify only the 
  end-points, no matter what path it is going to take (the 
  orchestrator can select a dynamic path) 

- Static Path - the user request a circuit and specify the end-points 
  as well as the path that should be taken (i.e. a static path was 
  chosen by user) 

- Alternative Route - A physical path that does not share any item 
  under MW

- Flexible backup path - an altenrative route that may not fulfils the
  user requirements, but at least that routes offers connectivity.

- Open mind user - the user requested a service with a flexible backup 
  path, i.e. the user has open mind to allow an alternative route in
  case the primary one is not available even through the alternative
  route does not fulfils the user requirements.

- Disable a service - Remove all flows related with the service 

- Enable a Service - Install all flows related with the service 

- Saved setup - the setup of the orchestration tool saved as a 
  snapshot considering all circuits, requirements, paths (primary and 
  secondary), flow mods that should be running on the switches, and 
  all other important information 

- Network Operator - a person who administrate the network and has 
  knowledge and autonomy to decide how the network should behavior


##########
References
##########

[A collection of URLs used as references.]


#########
Copyright
#########

This document is placed in the public domain or under the
CC0-1.0-Universal license, whichever is more permissive.
