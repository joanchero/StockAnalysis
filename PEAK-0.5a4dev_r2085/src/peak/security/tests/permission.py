"""Permission tests"""

from unittest import TestCase, makeSuite, TestSuite
from peak.api import *
from peak.tests import testRoot


class SimpleTests(TestCase):

    def setUp(self):
        self.context = security.Context()

    def checkUniversals(self):
        assert self.context.hasPermission(None, security.Anybody, None)
        assert not self.context.hasPermission(None, security.Nobody, None)


























class ManageAsset(security.Permission): pass
class ManageBatch(security.Permission): pass

class Worker(security.Permission): pass
class Manager(security.Permission): pass
class Shipper(security.Permission): pass
class Receiver(security.Permission): pass
class Owner(security.Permission): pass
class SelfOrManager(security.Permission): pass
class ShipmentViewer(security.Permission): pass

class Facility:

    binding.metadata(
        viewShipments = ShipmentViewer,
        manageWorkers = Manager,
    )

class Batch:
    binding.metadata(
        edit = ManageBatch,
        delete = Owner,
    )

class Shipment(Batch):
    binding.metadata(
        receiveShipment = Receiver,
        cancelShipment = Shipper
    )

class Asset(object):
    binding.metadata(
        edit = ManageAsset
    )

class Person(object):
    binding.metadata(
        edit = SelfOrManager
    )


class EquipmentRules(security.Context):

    [security.hasPermission.when("perm==Worker and subject in Shipment")]
    def checkWorkerForShipment(self, user, perm, subject):
        return self.hasPermission(user, Worker, subject.fromFacility
        ) or self.hasPermission(user, Worker, subject.toFacility
        ) or security.Denial(
            "You need to be a worker at either the origin or destination"
            " facility for this shipment."
        )

    [security.hasPermission.when("perm==Manager and subject in Person")]
    def checkSupervisor(self, user, perm, subject):
        return user is subject.supervisor or security.Denial(
            "You must be a supervisor of this person."
        )

    [security.hasPermission.when("perm==SelfOrManager")]
    def checkSelfOrManager(self, user, perm, subject):
        return user in (subject,subject.supervisor) or security.Denial(
            "You must be this person or their supervisor."
        )

    [security.hasPermission.when("perm in [ManageAsset, ShipmentViewer]")]
    def checkWorkerOrManager(self, user, perm, subject):
        return self.hasPermission(
            user, Worker, subject
        ) or self.hasPermission(user,Manager,subject) or security.Denial(
            "You need to be a worker or manager at the relevant facility"
        )

    [security.hasPermission.when("perm in [Worker, Manager]")]
    def checkPermissionsInPlace(self, user, perm, subject):
        # check same permission, but for location
        return self.hasPermission(user,perm,subject.location)






    [security.hasPermission.when("perm==ManageBatch")]
    def checkManageBatch(self, user, perm, subject):
        return (
            self.hasPermission(user,Owner,subject) or
            self.hasPermission(user,Worker,subject) or
            self.hasPermission(user,Manager,subject) or
            security.Denial(
                "You must be the batch's owner, or a worker or manager at"
                " the relevant facility."
            )
        )


    [security.hasPermission.when("perm==Shipper and subject in Shipment")]
    def checkShipper(self, user, perm, subject):
        return self.hasPermission(user, Worker, subject.fromFacility)

    [security.hasPermission.when("perm==Receiver and subject in Shipment")]
    def checkReceiver(self, user, perm, subject):
        return self.hasPermission(user, Worker, subject.toFacility)

    [security.hasPermission.when("perm==Worker and subject in Facility")]
    def checkWorkerForFacility(self, user, perm, subject):
        return user.facility is subject or security.Denial(
            "You must be a worker at the relevant facility."
        )

    [security.hasPermission.when("perm==Manager and subject in Facility")]
    def checkManagerForFacility(self, user, perm, subject):
        return user in subject.managers or security.Denial(
            "You must be a manager at the relevant facility"
        )

    [security.hasPermission.when("perm==Owner and subject in Batch")]
    def checkBatchOwner(self, user, perm, subject):
        return user is subject.owner or security.Denial(
            "You must be the batch's owner"
        )



NewYork = Facility()
NewYork.name = 'New York'
MrSmythe = Person()
Mickey = Person()

MrSmythe.name = 'Smythe'
MrSmythe.facility = NewYork
MrSmythe.supervisor = None

Mickey.name = 'Mickey D'
Mickey.facility = NewYork
Mickey.supervisor = MrSmythe

Paris = Facility()
Paris.name = 'Paris'
JeanPierre = Person()
BobChien = Person()

JeanPierre.name = 'J.P.'
JeanPierre.facility = Paris
JeanPierre.supervisor = None

BobChien.name = 'Bob le Chien'
BobChien.facility = Paris
BobChien.supervisor = JeanPierre

NewYork.managers = MrSmythe,
Paris.managers = JeanPierre,













Batch123 = Batch()
Batch123.name = 'Batch 123'
Batch123.location = NewYork
Batch123.owner = Mickey

MegaMachine = Asset()
MegaMachine.name = 'Mega Machine'
MegaMachine.location = Batch123

MegaDrive = Asset()
MegaDrive.name = 'Mega Drive'
MegaDrive.location = MegaMachine

Shipment16 = Shipment()
Shipment16.name = 'Shipment 16'
Shipment16.location = Paris
Shipment16.fromFacility = Paris
Shipment16.toFacility = NewYork
Shipment16.owner = BobChien

Thingy = Asset()
Thingy.name = 'Thingy'
Thingy.location = Shipment16


















scenarios = [

    (NewYork, 'viewShipments', [MrSmythe,Mickey]),
    (NewYork, 'manageWorkers', [MrSmythe]),
    (Paris, 'viewShipments', [JeanPierre,BobChien]),
    (Paris, 'manageWorkers', [JeanPierre]),

    (MrSmythe,'edit',[MrSmythe]),
    (Mickey,'edit',[Mickey,MrSmythe]),
    (JeanPierre,'edit',[JeanPierre]),
    (BobChien,'edit',[BobChien,JeanPierre]),

    (Shipment16,'cancelShipment',[JeanPierre,BobChien]),
    (Shipment16,'receiveShipment',[MrSmythe,Mickey]),
    (Shipment16,'edit',[MrSmythe, Mickey, JeanPierre, BobChien]),
    (Shipment16,'delete',[BobChien]),
    (Shipment16,'undefined',[]),

    (Thingy, 'edit', [MrSmythe, Mickey, JeanPierre, BobChien]),
    (MegaDrive, 'edit', [MrSmythe, Mickey]),
    (MegaMachine, 'edit', [MrSmythe, Mickey]),

    (Batch123, 'delete', [Mickey]),
    (Batch123, 'edit', [MrSmythe, Mickey]),
]

class ScenarioTests(TestCase):

    def assertAllowed(self, subject, name, users):
        context = EquipmentRules()
        perm = context.permissionFor(subject,name)
        for person in MrSmythe, Mickey, JeanPierre, BobChien:
            allowed = context.hasPermission(person,perm,subject)
            assert not allowed==(person not in users), (
                "%s fails for %s.%s" % (person.name, subject.name, name)
            )

    def checkScenarios(self):
        for s in scenarios:
            self.assertAllowed(*s)

TestClasses = (
    SimpleTests, ScenarioTests
)


def test_suite():
    return TestSuite([makeSuite(t,'check') for t in TestClasses])


































