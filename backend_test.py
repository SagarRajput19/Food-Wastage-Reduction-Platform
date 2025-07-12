#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Food Wastage Reduction Platform
Tests all endpoints with proper authentication and role-based access
"""

import requests
import sys
import json
from datetime import datetime
import uuid

class FoodWastageAPITester:
    def __init__(self, base_url="https://54355725-f7f6-4ade-8779-9c25b4720805.preview.emergentagent.com"):
        self.base_url = base_url
        self.donor_token = None
        self.ngo_token = None
        self.donor_user = None
        self.ngo_user = None
        self.test_listing_id = None
        self.test_request_id = None
        self.tests_run = 0
        self.tests_passed = 0

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED {details}")
        else:
            print(f"❌ {name} - FAILED {details}")
        return success

    def make_request(self, method, endpoint, data=None, token=None, expected_status=200):
        """Make HTTP request with proper headers"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            success = response.status_code == expected_status
            response_data = {}
            
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}

            return success, response.status_code, response_data

        except Exception as e:
            return False, 0, {"error": str(e)}

    def test_health_check(self):
        """Test basic health endpoint"""
        success, status, data = self.make_request('GET', 'api/health')
        return self.log_test(
            "Health Check", 
            success and data.get('status') == 'healthy',
            f"Status: {status}, Response: {data}"
        )

    def test_user_registration(self):
        """Test user registration for both donor and NGO"""
        timestamp = datetime.now().strftime('%H%M%S')
        
        # Test donor registration
        donor_data = {
            "name": f"Test Donor {timestamp}",
            "email": f"donor_{timestamp}@test.com",
            "password": "TestPass123!",
            "role": "donor",
            "phone": "1234567890",
            "address": "123 Test Street, Test City",
            "organization": "Test Restaurant"
        }
        
        success, status, data = self.make_request('POST', 'api/auth/register', donor_data, expected_status=200)
        donor_success = self.log_test(
            "Donor Registration",
            success and 'token' in data,
            f"Status: {status}"
        )
        
        if donor_success:
            self.donor_token = data['token']
            self.donor_user = data['user']

        # Test NGO registration
        ngo_data = {
            "name": f"Test NGO {timestamp}",
            "email": f"ngo_{timestamp}@test.com", 
            "password": "TestPass123!",
            "role": "ngo",
            "phone": "0987654321",
            "address": "456 NGO Street, NGO City",
            "organization": "Test NGO Foundation"
        }
        
        success, status, data = self.make_request('POST', 'api/auth/register', ngo_data, expected_status=200)
        ngo_success = self.log_test(
            "NGO Registration",
            success and 'token' in data,
            f"Status: {status}"
        )
        
        if ngo_success:
            self.ngo_token = data['token']
            self.ngo_user = data['user']

        return donor_success and ngo_success

    def test_user_login(self):
        """Test user login functionality"""
        if not self.donor_user or not self.ngo_user:
            return self.log_test("User Login", False, "Registration failed, cannot test login")

        # Test donor login
        donor_login = {
            "email": self.donor_user['email'],
            "password": "TestPass123!"
        }
        
        success, status, data = self.make_request('POST', 'api/auth/login', donor_login, expected_status=200)
        donor_login_success = self.log_test(
            "Donor Login",
            success and 'token' in data,
            f"Status: {status}"
        )

        # Test NGO login
        ngo_login = {
            "email": self.ngo_user['email'],
            "password": "TestPass123!"
        }
        
        success, status, data = self.make_request('POST', 'api/auth/login', ngo_login, expected_status=200)
        ngo_login_success = self.log_test(
            "NGO Login",
            success and 'token' in data,
            f"Status: {status}"
        )

        return donor_login_success and ngo_login_success

    def test_get_current_user(self):
        """Test getting current user info"""
        if not self.donor_token:
            return self.log_test("Get Current User", False, "No donor token available")

        success, status, data = self.make_request('GET', 'api/auth/me', token=self.donor_token)
        return self.log_test(
            "Get Current User",
            success and data.get('role') == 'donor',
            f"Status: {status}, Role: {data.get('role')}"
        )

    def test_create_food_listing(self):
        """Test creating food listing (donor only)"""
        if not self.donor_token:
            return self.log_test("Create Food Listing", False, "No donor token available")

        listing_data = {
            "title": "Test Fresh Biryani",
            "description": "Delicious vegetable biryani, freshly prepared",
            "quantity": "20 plates",
            "food_type": "veg",
            "pickup_address": "123 Restaurant Street, Food City, 12345",
            "expiry_hours": 4,
            "image_url": "https://example.com/biryani.jpg"
        }

        success, status, data = self.make_request('POST', 'api/listings', listing_data, self.donor_token, expected_status=200)
        listing_success = self.log_test(
            "Create Food Listing",
            success and 'listing_id' in data,
            f"Status: {status}"
        )

        if listing_success:
            self.test_listing_id = data['listing_id']

        return listing_success

    def test_get_listings(self):
        """Test getting listings for both donor and NGO"""
        if not self.donor_token or not self.ngo_token:
            return self.log_test("Get Listings", False, "Missing tokens")

        # Test donor getting their own listings
        success, status, data = self.make_request('GET', 'api/listings', token=self.donor_token)
        donor_listings_success = self.log_test(
            "Get Donor Listings",
            success and 'listings' in data,
            f"Status: {status}, Count: {len(data.get('listings', []))}"
        )

        # Test NGO getting available listings
        success, status, data = self.make_request('GET', 'api/listings', token=self.ngo_token)
        ngo_listings_success = self.log_test(
            "Get NGO Listings",
            success and 'listings' in data,
            f"Status: {status}, Count: {len(data.get('listings', []))}"
        )

        return donor_listings_success and ngo_listings_success

    def test_get_listing_details(self):
        """Test getting specific listing details"""
        if not self.test_listing_id or not self.donor_token:
            return self.log_test("Get Listing Details", False, "No listing ID or token available")

        success, status, data = self.make_request('GET', f'api/listings/{self.test_listing_id}', token=self.donor_token)
        return self.log_test(
            "Get Listing Details",
            success and data.get('listing_id') == self.test_listing_id,
            f"Status: {status}"
        )

    def test_request_pickup(self):
        """Test NGO requesting pickup"""
        if not self.test_listing_id or not self.ngo_token:
            return self.log_test("Request Pickup", False, "No listing ID or NGO token available")

        request_data = {
            "listing_id": self.test_listing_id,
            "message": "We would like to pick up this food for our community kitchen"
        }

        success, status, data = self.make_request('POST', f'api/listings/{self.test_listing_id}/request', request_data, self.ngo_token, expected_status=200)
        request_success = self.log_test(
            "Request Pickup",
            success and 'request_id' in data,
            f"Status: {status}"
        )

        if request_success:
            self.test_request_id = data['request_id']

        return request_success

    def test_handle_request_action(self):
        """Test donor accepting/rejecting pickup requests"""
        if not self.test_request_id or not self.donor_token:
            return self.log_test("Handle Request Action", False, "No request ID or donor token available")

        # Test accepting the request
        action_data = {
            "request_id": self.test_request_id,
            "action": "accept"
        }

        success, status, data = self.make_request('POST', f'api/requests/{self.test_request_id}/action', action_data, self.donor_token, expected_status=200)
        return self.log_test(
            "Accept Pickup Request",
            success and 'message' in data,
            f"Status: {status}, Message: {data.get('message')}"
        )

    def test_mark_pickup_complete(self):
        """Test marking pickup as complete"""
        if not self.test_listing_id or not self.donor_token:
            return self.log_test("Mark Pickup Complete", False, "No listing ID or donor token available")

        success, status, data = self.make_request('POST', f'api/listings/{self.test_listing_id}/complete', token=self.donor_token, expected_status=200)
        return self.log_test(
            "Mark Pickup Complete",
            success and 'message' in data,
            f"Status: {status}, Message: {data.get('message')}"
        )

    def test_dashboard_stats(self):
        """Test dashboard statistics for both roles"""
        if not self.donor_token or not self.ngo_token:
            return self.log_test("Dashboard Stats", False, "Missing tokens")

        # Test donor stats
        success, status, data = self.make_request('GET', 'api/dashboard/stats', token=self.donor_token)
        donor_stats_success = self.log_test(
            "Donor Dashboard Stats",
            success and data.get('role') == 'donor',
            f"Status: {status}, Stats: {data}"
        )

        # Test NGO stats
        success, status, data = self.make_request('GET', 'api/dashboard/stats', token=self.ngo_token)
        ngo_stats_success = self.log_test(
            "NGO Dashboard Stats",
            success and data.get('role') == 'ngo',
            f"Status: {status}, Stats: {data}"
        )

        return donor_stats_success and ngo_stats_success

    def test_unauthorized_access(self):
        """Test unauthorized access scenarios"""
        # Test accessing protected endpoint without token
        success, status, data = self.make_request('GET', 'api/auth/me', expected_status=403)
        no_token_test = self.log_test(
            "No Token Access",
            not success and status == 403,
            f"Status: {status}"
        )

        # Test NGO trying to create listing (should fail)
        if self.ngo_token:
            listing_data = {
                "title": "Unauthorized Listing",
                "description": "This should fail",
                "quantity": "10 plates",
                "food_type": "veg",
                "pickup_address": "Test Address",
                "expiry_hours": 2
            }
            success, status, data = self.make_request('POST', 'api/listings', listing_data, self.ngo_token, expected_status=403)
            ngo_create_test = self.log_test(
                "NGO Create Listing (Should Fail)",
                not success and status == 403,
                f"Status: {status}"
            )
        else:
            ngo_create_test = False

        return no_token_test and ngo_create_test

    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("🚀 Starting Food Wastage Platform API Tests")
        print("=" * 60)

        # Basic connectivity
        if not self.test_health_check():
            print("❌ Health check failed - stopping tests")
            return False

        # Authentication tests
        if not self.test_user_registration():
            print("❌ User registration failed - stopping tests")
            return False

        self.test_user_login()
        self.test_get_current_user()

        # Core functionality tests
        self.test_create_food_listing()
        self.test_get_listings()
        self.test_get_listing_details()
        self.test_request_pickup()
        self.test_handle_request_action()
        self.test_mark_pickup_complete()
        self.test_dashboard_stats()

        # Security tests
        self.test_unauthorized_access()

        # Print final results
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed! Backend API is working correctly.")
            return True
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed. Check the issues above.")
            return False

def main():
    """Main test execution"""
    print("Food Wastage Reduction Platform - Backend API Testing")
    print(f"Testing against: https://54355725-f7f6-4ade-8779-9c25b4720805.preview.emergentagent.com")
    print()

    tester = FoodWastageAPITester()
    success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())