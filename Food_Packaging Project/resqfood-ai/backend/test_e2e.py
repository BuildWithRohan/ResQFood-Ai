"""End-to-end API test for ResQFood AI."""
import httpx
import sys

base = 'http://localhost:8000'

try:
    # 1. Login as admin
    print('=== 1. Login Test ===')
    r = httpx.post(base + '/api/auth/login', json={'email':'admin@resqfood.ai','password':'admin123'})
    token = r.json()['access_token']
    print('Admin login: %d - Token OK' % r.status_code)
    headers = {'Authorization': 'Bearer ' + token}

    # 2. Get analytics
    print('\n=== 2. Analytics/Impact ===')
    r = httpx.get(base + '/api/analytics/impact', headers=headers)
    data = r.json()
    print('Impact status: %d' % r.status_code)
    for k, v in data.items():
        print('  %s: %s' % (k, v))

    # 3. Kitchen predictions
    print('\n=== 3. Kitchen - Demand Predictions ===')
    r = httpx.post(base + '/api/auth/login', json={'email':'kitchen@abccollege.edu','password':'kitchen123'})
    kt = r.json()['access_token']
    kh = {'Authorization': 'Bearer ' + kt}
    r = httpx.get(base + '/api/demand/predictions', headers=kh)
    preds = r.json()
    if preds:
        p = preds[0]
        print('Prediction: demand=%s, recommended=%s, MAE=%s' % (
            p.get('predicted_demand'), p.get('recommended_production'), p.get('mae')))

    # 4. Get surplus
    print('\n=== 4. Surplus Food ===')
    r = httpx.get(base + '/api/surplus/', headers=kh)
    surplus_list = r.json()
    for s in surplus_list:
        print('  %s - %s %s - status: %s' % (s['food_name'], s['quantity'], s['unit'], s['status']))

    # 5. Get requests
    print('\n=== 5. NGO Requests ===')
    r = httpx.get(base + '/api/requests/', headers=headers)
    reqs = r.json()
    for rq in reqs:
        print('  qty=%s, urgency=%s, status=%s' % (rq['requested_quantity'], rq['urgency'], rq['status']))

    # 6. Run allocation
    print('\n=== 6. Run Smart Allocation ===')
    surplus_id = surplus_list[0]['id'] if surplus_list else 1
    r = httpx.post(base + '/api/allocation/run', json={'surplus_id': surplus_id}, headers=headers)
    if r.status_code == 200:
        alloc = r.json()
        print('Total available: %s' % alloc.get('total_available'))
        print('Total requested: %s' % alloc.get('total_requested'))
        print('Total allocated: %s' % alloc.get('total_allocated'))
        print('Unfulfilled: %s' % alloc.get('unfulfilled'))
        for a in alloc.get('allocations', []):
            print('  -> %s: requested=%s, allocated=%s, priority=%.2f' % (
                a.get('ngo_name'), a.get('requested_quantity'), a.get('allocated_quantity'), a.get('priority_score', 0)))
            for f in a.get('factors', []):
                print('     [%s] %s' % (f.get('impact'), f.get('factor_label')))
    else:
        print('Allocation error: %d %s' % (r.status_code, r.text[:200]))

    # 7. Create delivery
    print('\n=== 7. Create Delivery ===')
    r = httpx.post(base + '/api/deliveries/', json={'surplus_id': surplus_id}, headers=headers)
    if r.status_code == 200:
        d = r.json()
        print('Delivery #%s: %s meals, %s stops' % (d.get('id'), d.get('total_meals'), d.get('total_stops')))
        for stop in d.get('stops', []):
            print('  Stop %s: %s - %s meals' % (stop.get('sequence_order'), stop.get('ngo_name'), stop.get('quantity')))
    else:
        print('Delivery error: %d %s' % (r.status_code, r.text[:200]))

    print('\n=== ALL API TESTS PASSED ===')

except Exception as e:
    print('ERROR: %s' % str(e))
    import traceback
    traceback.print_exc()
    sys.exit(1)
