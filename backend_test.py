import requests
import sys
import json
from datetime import datetime

class SIPROAPITester:
    def __init__(self, base_url="https://sipro-dev-env.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.session = requests.Session()

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        if headers:
            test_headers.update(headers)
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=test_headers)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=test_headers)
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=test_headers)

            print(f"   Status: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if 'data' in response_data:
                        print(f"   Response: {type(response_data['data'])} with {len(response_data['data']) if isinstance(response_data['data'], list) else 'object'}")
                except:
                    pass
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Error: {response.text[:200]}")

            return success, response.json() if response.headers.get('content-type', '').startswith('application/json') else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_login(self):
        """Test login and get token"""
        print("\n" + "="*50)
        print("TESTING AUTHENTICATION")
        print("="*50)
        
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@sipro.com", "password": "admin123"}
        )
        if success and 'token' in response:
            self.token = response['token']
            print(f"   Token received: {self.token[:20]}...")
            return True
        return False

    def test_dashboard(self):
        """Test dashboard endpoint - Phase B Enhancement"""
        print("\n" + "="*50)
        print("TESTING DASHBOARD - PHASE B ENHANCEMENT")
        print("="*50)
        
        success, response = self.run_test(
            "Dashboard Data",
            "GET",
            "dashboard",
            200
        )
        
        if success and response.get('data'):
            data = response['data']
            # Check for required Phase A fields
            required_fields = ['lead_stages', 'my_leads', 'unassigned_leads', 'my_appointments']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                print(f"❌ Missing required dashboard fields: {missing_fields}")
                return False
            
            # Check for Phase B enhancement fields
            phase_b_fields = ['avg_response_minutes', 'responded_leads', 'pending_assignments']
            phase_b_missing = [field for field in phase_b_fields if field not in data]
            
            if phase_b_missing:
                print(f"⚠️  Missing Phase B dashboard fields: {phase_b_missing}")
            else:
                print(f"✅ Phase B dashboard fields found: avg_response_minutes={data.get('avg_response_minutes')}, responded_leads={data.get('responded_leads')}, pending_assignments={data.get('pending_assignments')}")
            
            # Check lead_stages structure
            if 'lead_stages' in data:
                stages = data['lead_stages']
                expected_stages = ['acquisition', 'nurturing', 'appointment', 'booking', 'recycle']
                for stage in expected_stages:
                    if stage not in stages:
                        print(f"❌ Missing stage in lead_stages: {stage}")
                        return False
                print(f"✅ Lead stages found: {stages}")
            
            print(f"✅ Dashboard API returns required Phase A fields")
        
        return success

    def test_projects(self):
        """Test projects endpoints"""
        print("\n" + "="*50)
        print("TESTING PROJECTS")
        print("="*50)
        
        # List projects
        success1, response = self.run_test(
            "List Projects",
            "GET",
            "projects",
            200
        )
        
        # Test with search
        success2, _ = self.run_test(
            "Search Projects",
            "GET",
            "projects?search=Grand",
            200
        )
        
        return success1 and success2

    def test_units(self):
        """Test units endpoints"""
        print("\n" + "="*50)
        print("TESTING UNITS")
        print("="*50)
        
        # List units
        success1, response = self.run_test(
            "List Units",
            "GET",
            "units",
            200
        )
        
        # Test with filters
        success2, _ = self.run_test(
            "Filter Units by Status",
            "GET",
            "units?status=available",
            200
        )
        
        return success1 and success2

    def test_leads(self):
        """Test CRM/leads endpoints - Phase B Enhancement"""
        print("\n" + "="*50)
        print("TESTING CRM/LEADS - PHASE B ENHANCEMENT")
        print("="*50)
        
        # List all leads
        success1, response = self.run_test(
            "List All Leads",
            "GET",
            "leads",
            200
        )
        
        # Test stage filtering - key Phase A feature
        success2, acq_response = self.run_test(
            "Filter Leads by Stage: Acquisition",
            "GET",
            "leads?stage=acquisition",
            200
        )
        
        success3, nur_response = self.run_test(
            "Filter Leads by Stage: Nurturing", 
            "GET",
            "leads?stage=nurturing",
            200
        )
        
        success4, apt_response = self.run_test(
            "Filter Leads by Stage: Appointment",
            "GET", 
            "leads?stage=appointment",
            200
        )
        
        success5, bkg_response = self.run_test(
            "Filter Leads by Stage: Booking",
            "GET",
            "leads?stage=booking", 
            200
        )
        
        success6, rec_response = self.run_test(
            "Filter Leads by Stage: Recycle",
            "GET",
            "leads?stage=recycle",
            200
        )
        
        # Test lead pipeline
        success7, pipeline_response = self.run_test(
            "Get Lead Pipeline",
            "GET",
            "leads/pipeline",
            200
        )
        
        if success7 and pipeline_response.get('data'):
            pipeline = pipeline_response['data']
            if 'stages' in pipeline:
                stages = pipeline['stages']
                print(f"✅ Pipeline stages: {stages}")
        
        # Test Phase B: Response Stats API
        success8, stats_response = self.run_test(
            "Get Lead Response Stats (Phase B)",
            "GET",
            "leads/response-stats",
            200
        )
        
        if success8 and stats_response.get('data'):
            stats = stats_response['data']
            required_stats = ['avg_response_minutes', 'waiting_for_contact', 'avg_wait_minutes', 'count']
            missing_stats = [field for field in required_stats if field not in stats]
            if missing_stats:
                print(f"❌ Missing response stats fields: {missing_stats}")
            else:
                print(f"✅ Response stats: avg_response={stats.get('avg_response_minutes')}m, waiting={stats.get('waiting_for_contact')}, avg_wait={stats.get('avg_wait_minutes')}m")
        
        # Create a test lead with stage
        test_lead_data = {
            "name": f"Test Lead {datetime.now().strftime('%H%M%S')}",
            "phone": f"+6281{datetime.now().strftime('%H%M%S')}",
            "email": f"test{datetime.now().strftime('%H%M%S')}@test.com",
            "source": "manual",
            "stage": "acquisition",
            "notes": "Test lead created by automated test"
        }
        
        success9, lead_response = self.run_test(
            "Create Lead with Stage",
            "POST",
            "leads",
            200,
            data=test_lead_data
        )
        
        # Store lead ID for further testing
        test_lead_id = None
        if success9 and lead_response.get('data'):
            test_lead_id = lead_response['data'].get('id')
            print(f"✅ Created test lead with ID: {test_lead_id}")
        
        # Test Phase B: Stage Transition API
        success10 = True
        if test_lead_id:
            success10, transition_response = self.run_test(
                "Stage Transition: Acquisition to Nurturing (Phase B)",
                "POST",
                f"leads/{test_lead_id}/transition",
                200,
                data={"stage": "nurturing", "reason": "Initial contact made"}
            )
            
            if success10 and transition_response.get('data'):
                lead_data = transition_response['data']
                if lead_data.get('stage') == 'nurturing':
                    print(f"✅ Stage transition successful: {lead_data.get('stage')}")
                    if 'response_time_minutes' in lead_data:
                        print(f"✅ Response time computed: {lead_data.get('response_time_minutes')} minutes")
                else:
                    print(f"❌ Stage transition failed: expected 'nurturing', got '{lead_data.get('stage')}'")
                    success10 = False
        
        # Test Phase B: Timeline API
        success11 = True
        if test_lead_id:
            success11, timeline_response = self.run_test(
                "Get Lead Timeline (Phase B)",
                "GET",
                f"leads/{test_lead_id}/timeline",
                200
            )
            
            if success11 and timeline_response.get('data'):
                timeline = timeline_response['data']
                print(f"✅ Timeline retrieved with {len(timeline)} events")
                # Check for different event types
                event_types = set(item.get('type') for item in timeline)
                print(f"   Event types: {event_types}")
        
        return all([success1, success2, success3, success4, success5, success6, success7, success8, success9, success10, success11])

    def test_deals(self):
        """Test deals endpoints"""
        print("\n" + "="*50)
        print("TESTING DEALS")
        print("="*50)
        
        # List deals
        success1, response = self.run_test(
            "List Deals",
            "GET",
            "deals",
            200
        )
        
        # Test with filters
        success2, _ = self.run_test(
            "Filter Deals by Status",
            "GET",
            "deals?status=active",
            200
        )
        
        return success1 and success2

    def test_siteplan(self):
        """Test siteplan endpoints"""
        print("\n" + "="*50)
        print("TESTING SITEPLAN")
        print("="*50)
        
        # Get siteplan for first project (assuming proj-001 exists from seed data)
        success1, response = self.run_test(
            "Get Siteplan",
            "GET",
            "siteplan/proj-001",
            200
        )
        
        # Test different view modes
        success2, _ = self.run_test(
            "Siteplan Construction View",
            "GET",
            "siteplan/proj-001?view_mode=construction",
            200
        )
        
        return success1 and success2

    def test_whatsapp(self):
        """Test WhatsApp endpoints (MOCKED)"""
        print("\n" + "="*50)
        print("TESTING WHATSAPP (MOCKED)")
        print("="*50)
        
        # List messages
        success1, response = self.run_test(
            "List WhatsApp Messages",
            "GET",
            "whatsapp/messages",
            200
        )
        
        # Send test message (mocked)
        test_message = {
            "recipient_phone": "+628123456789",
            "recipient_name": "Test User",
            "message": "Test message from automated test",
            "message_type": "notification"
        }
        
        success2, _ = self.run_test(
            "Send WhatsApp Message (MOCKED)",
            "POST",
            "whatsapp/send",
            200,
            data=test_message
        )
        
        return success1 and success2

    def test_dev_report(self):
        """Test development report endpoints"""
        print("\n" + "="*50)
        print("TESTING DEV REPORT")
        print("="*50)
        
        # Get dev report
        success1, response = self.run_test(
            "Get Dev Report",
            "GET",
            "dev-report",
            200
        )
        
        return success1

    def test_lead_import(self):
        """Test lead import functionality"""
        print("\n" + "="*50)
        print("TESTING LEAD IMPORT")
        print("="*50)
        
        # Test lead import
        import_data = {
            "leads": [
                {
                    "name": f"Import Test {datetime.now().strftime('%H%M%S')}",
                    "phone": f"+6281{datetime.now().strftime('%H%M%S')}",
                    "email": f"import{datetime.now().strftime('%H%M%S')}@test.com",
                    "notes": "Imported via automated test"
                }
            ],
            "source": "csv_import",
            "campaign": "Test Campaign"
        }
        
        success, response = self.run_test(
            "Import Leads",
            "POST",
            "leads/import",
            200,
            data=import_data
        )
        
        return success

    def test_finance(self):
        """Test Finance Module APIs (Phase 2)"""
        print("\n" + "="*50)
        print("TESTING FINANCE MODULE (PHASE 2)")
        print("="*50)
        
        # Test finance summary
        success1, response = self.run_test(
            "Finance Summary",
            "GET",
            "finance/summary",
            200
        )
        
        # Test billing schedules
        success2, _ = self.run_test(
            "List Billing Schedules",
            "GET",
            "finance/billing",
            200
        )
        
        # Test payments
        success3, _ = self.run_test(
            "List Payments",
            "GET",
            "finance/payments",
            200
        )
        
        return success1 and success2 and success3

    def test_construction(self):
        """Test Construction Module APIs (Phase 2)"""
        print("\n" + "="*50)
        print("TESTING CONSTRUCTION MODULE (PHASE 2)")
        print("="*50)
        
        # Test construction summary
        success1, response = self.run_test(
            "Construction Summary",
            "GET",
            "construction/summary",
            200
        )
        
        # Test construction units
        success2, _ = self.run_test(
            "List Construction Units",
            "GET",
            "construction/units",
            200
        )
        
        return success1 and success2

    def test_notifications(self):
        """Test Notification Center APIs (Phase 2)"""
        print("\n" + "="*50)
        print("TESTING NOTIFICATION CENTER (PHASE 2)")
        print("="*50)
        
        # Test notifications list
        success1, response = self.run_test(
            "List Notifications",
            "GET",
            "notifications",
            200
        )
        
        # Test auto follow-up rules
        success2, _ = self.run_test(
            "List Auto Follow-Up Rules",
            "GET",
            "notifications/auto-rules",
            200
        )
        
        # Test create notification
        test_notification = {
            "title": "Test Notification",
            "message": "This is a test notification from automated test",
            "type": "info",
            "target_user": "all"
        }
        
        success3, _ = self.run_test(
            "Create Notification",
            "POST",
            "notifications",
            200,
            data=test_notification
        )
        
        return success1 and success2 and success3

    def test_assignment_system(self):
        """Test Assignment System APIs (Phase B)"""
        print("\n" + "="*50)
        print("TESTING ASSIGNMENT SYSTEM (PHASE B)")
        print("="*50)
        
        # First, get some leads to work with
        success1, leads_response = self.run_test(
            "Get Leads for Assignment Testing",
            "GET",
            "leads?stage=acquisition&limit=3",
            200
        )
        
        if not success1 or not leads_response.get('data'):
            print("❌ No leads available for assignment testing")
            return False
        
        leads = leads_response['data']
        if len(leads) == 0:
            print("❌ No acquisition leads found for assignment testing")
            return False
        
        # Get first lead for testing
        test_lead_id = leads[0]['id']
        print(f"✅ Using lead {test_lead_id} for assignment testing")
        
        # Test manual assignment
        assign_data = {
            "lead_ids": [test_lead_id],
            "assigned_to": "admin@sipro.com",
            "reason": "Manual assignment for testing"
        }
        
        success2, assign_response = self.run_test(
            "Manual Lead Assignment",
            "POST",
            "leads/assign",
            200,
            data=assign_data
        )
        
        if success2 and assign_response.get('data'):
            assigned_count = assign_response['data'].get('assigned', 0)
            print(f"✅ Manually assigned {assigned_count} lead(s)")
        
        # Test assignment response - accept
        success3, accept_response = self.run_test(
            "Accept Assignment",
            "POST",
            f"leads/{test_lead_id}/assignment/respond",
            200,
            data={"lead_id": test_lead_id, "action": "accept"}
        )
        
        if success3 and accept_response.get('data'):
            lead_data = accept_response['data']
            if lead_data.get('assignment_status') == 'accepted':
                print(f"✅ Assignment accepted successfully")
            else:
                print(f"❌ Assignment status not updated: {lead_data.get('assignment_status')}")
                success3 = False
        
        # Test auto-assignment
        success4, auto_assign_response = self.run_test(
            "Auto-Assign Leads",
            "POST",
            "leads/auto-assign",
            200,
            data={"stage": "acquisition", "role": "sales"}
        )
        
        if success4 and auto_assign_response.get('data'):
            auto_assigned = auto_assign_response['data'].get('assigned', 0)
            print(f"✅ Auto-assigned {auto_assigned} lead(s)")
        
        return all([success1, success2, success3, success4])

    def test_appointments(self):
        """Test Appointment Calendar APIs (Phase 2)"""
        print("\n" + "="*50)
        print("TESTING APPOINTMENT CALENDAR (PHASE 2)")
        print("="*50)
        
        # Test appointments calendar
        current_month = datetime.now().strftime('%Y-%m')
        success1, response = self.run_test(
            "Get Appointment Calendar",
            "GET",
            f"appointments/calendar?month={current_month}",
            200
        )
        
        # Test appointments list
        success2, _ = self.run_test(
            "List Appointments",
            "GET",
            "appointments",
            200
        )
        
        return success1 and success2

def main():
    print("🚀 Starting SIPRO API Testing (Phase B)...")
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("📋 Testing Phase B features: Assignment System, Stage Transitions, Response Time Tracking")
    
    # Setup
    tester = SIPROAPITester()
    
    # Run authentication test first
    if not tester.test_login():
        print("\n❌ Authentication failed, stopping tests")
        return 1

    # Run all API tests
    test_results = []
    test_results.append(("Dashboard", tester.test_dashboard()))
    test_results.append(("Projects", tester.test_projects()))
    test_results.append(("Units", tester.test_units()))
    test_results.append(("CRM/Leads", tester.test_leads()))
    test_results.append(("Assignment System (Phase B)", tester.test_assignment_system()))
    test_results.append(("Deals", tester.test_deals()))
    test_results.append(("Siteplan", tester.test_siteplan()))
    test_results.append(("WhatsApp", tester.test_whatsapp()))
    test_results.append(("Dev Report", tester.test_dev_report()))
    test_results.append(("Lead Import", tester.test_lead_import()))
    
    # Phase 2 Features
    test_results.append(("Finance Module", tester.test_finance()))
    test_results.append(("Construction Module", tester.test_construction()))
    test_results.append(("Notification Center", tester.test_notifications()))
    test_results.append(("Appointment Calendar", tester.test_appointments()))

    # Print final results
    print("\n" + "="*60)
    print("📊 FINAL TEST RESULTS")
    print("="*60)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<20} {status}")
    
    print(f"\n📈 Overall: {tester.tests_passed}/{tester.tests_run} tests passed")
    success_rate = (tester.tests_passed / tester.tests_run * 100) if tester.tests_run > 0 else 0
    print(f"📊 Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("🎉 Backend API testing completed successfully!")
        return 0
    else:
        print("⚠️  Some API tests failed. Check the logs above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())