# Reservation Workflow Design

## Overview
This document outlines the design for implementing a complete reservation workflow for properties with status transitions, permissions, and audit trail.

## Database Schema

### 1. Reservations Table
```sql
CREATE TABLE reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id),
    user_id UUID NOT NULL REFERENCES users(id),  -- Sales person who created reservation
    customer_name VARCHAR(255) NOT NULL,
    customer_email VARCHAR(255),
    customer_phone VARCHAR(50),
    
    -- Financial details
    equity_amount DECIMAL(10,2),  -- Eigenkapital
    equity_percentage DECIMAL(5,2),  -- Eigenkapital percentage
    is_90_10_deal BOOLEAN DEFAULT FALSE,  -- 90/10 deal flag
    adjusted_purchase_price DECIMAL(10,2),  -- Modified price for 90/10
    external_commission DECIMAL(10,2),  -- Externe Maklercortage
    internal_commission DECIMAL(10,2),  -- Interne Provision
    reservation_fee_paid BOOLEAN DEFAULT FALSE,  -- Set when moving to Reserviert
    reservation_fee_paid_date DATE,  -- Date when reservation fee was paid
    
    -- Notary details
    preferred_notary VARCHAR(255),  -- Notarwunsch (can be empty)
    notary_appointment_date DATE,  -- Date of notary appointment
    notary_appointment_time TIME,  -- Time of notary appointment
    notary_location VARCHAR(500),  -- Location/address of notary appointment
    
    -- Status tracking
    status INTEGER NOT NULL DEFAULT 5,  -- Current reservation status (matches property.active values)
    is_active BOOLEAN DEFAULT TRUE,  -- Whether this is the active reservation or on waitlist
    waitlist_position INTEGER,  -- Position in waitlist (NULL if active)
    
    -- Notes and documentation
    notes TEXT,
    cancellation_reason TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    
    CONSTRAINT fk_property FOREIGN KEY (property_id) REFERENCES properties(id)
);
```

### 2. Reservation Status History Table
```sql
CREATE TABLE reservation_status_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reservation_id UUID NOT NULL REFERENCES reservations(id),
    from_status INTEGER,
    to_status INTEGER NOT NULL,
    changed_by UUID NOT NULL REFERENCES users(id),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    
    CONSTRAINT fk_reservation FOREIGN KEY (reservation_id) REFERENCES reservations(id)
);
```

### 3. Property Table Updates
- The existing `active` field will continue to represent property status
- When a reservation is created/updated, it will sync with property.active

## State Machine Design

### Status Values (Same as Property.active)
- `0` = Verkauft (Sold)
- `1` = Frei (Available)
- `5` = Angefragt (Requested)
- `6` = Reserviert (Reserved)
- `7` = Notartermin (Notary Appointment)
- `9` = Notarvorbereitung (Notary Preparation)

### Reservation Lifecycle
1. Property starts as `1` (Frei)
2. Sales person creates reservation → status becomes `5` (Angefragt)
3. Property Manager approves → status becomes `6` (Reserviert)
4. Prepare for notary → status becomes `9` (Notarvorbereitung)
5. Schedule notary → status becomes `7` (Notartermin)
6. Complete sale → status becomes `0` (Verkauft)
7. OR Cancel at any point → next waitlist reservation becomes active or property returns to `1` (Frei)

### Waitlist System
- Only ONE reservation can be `is_active = true` per property
- Active reservation controls the property status (property.active)
- Additional reservations are placed on waitlist with `is_active = false`
- Waitlist reservations have `waitlist_position` (1, 2, 3, etc.)
- Waitlist reservations remain in status `5` (Angefragt) until activated
- When active reservation is cancelled:
  - Next waitlist reservation (position 1) becomes active automatically
  - All other waitlist positions are decremented
  - Property status updates to new active reservation's status

### Waitlist Management (Property Manager/Tenant Admin only)
- Can reorder waitlist positions
- Can promote any waitlist reservation to active status
- When promoting from waitlist:
  - Current active reservation moves to waitlist position 1
  - Promoted reservation becomes active
  - Property status updates accordingly
- Common scenarios:
  - Customer on waitlist paid reservation fee first → promote to active
  - Better qualified buyer on waitlist → promote to active
  - Active reservation not responding → swap with waitlist

### State Transitions
```
Status 1 (Frei) 
    → 5 (Angefragt) - by Sales Person creating reservation
    
Status 5 (Angefragt)
    → 6 (Reserviert) - by Property Manager/Tenant Admin (must set reservation_fee_paid)
    → 1 (Frei) - by cancellation
    
Status 6 (Reserviert)
    → 9 (Notarvorbereitung) - by Property Manager/Tenant Admin
    → 1 (Frei) - by cancellation
    
Status 9 (Notarvorbereitung)
    → 7 (Notartermin) - by Property Manager/Tenant Admin (requires date/time)
    → 1 (Frei) - by cancellation
    
Status 7 (Notartermin)
    → 0 (Verkauft) - by Property Manager/Tenant Admin
    → 1 (Frei) - by cancellation
    
Status 0 (Verkauft)
    → No transitions (final state)
```

## Permission Model

### New Permissions
- `reservations:create` - Create new reservations
- `reservations:read` - View reservations
- `reservations:update` - Update reservation details
- `reservations:delete` - Delete reservations
- `reservations:manage` - Manage all reservations (status transitions)

### Role-Based Access
1. **Sales Person**
   - Can create reservations for free properties
   - Can cancel their own reservations
   - Can view their own reservations
   - Cannot change status beyond initial request

2. **Location Manager**
   - Can view all reservations from their team
   - Cannot change reservation status

3. **Property Manager / Tenant Admin**
   - Can view all reservations
   - Can change reservation status (all transitions)
   - Can cancel any reservation
   - Can update reservation details

## API Endpoints

### Reservation Management
```
POST   /api/v1/properties/{property_id}/reservations  # Create reservation (active or waitlist)
GET    /api/v1/reservations                          # List reservations (filtered by role)
GET    /api/v1/reservations/{id}                     # Get reservation details
PUT    /api/v1/reservations/{id}                     # Update reservation
DELETE /api/v1/reservations/{id}                     # Cancel reservation
POST   /api/v1/reservations/{id}/status              # Change reservation status
GET    /api/v1/reservations/{id}/history             # Get status history
POST   /api/v1/reservations/{id}/promote             # Promote from waitlist to active
PUT    /api/v1/properties/{property_id}/waitlist     # Reorder waitlist
```

### Property Integration
```
GET    /api/v1/properties/{id}/reservation           # Get active reservation for property
```

## Frontend Components

### 1. Reservation Button (Property Detail Page)
- Show "Reservieren" button for properties with active = 1 (Frei)
- Check user permission `reservations:create`
- Open reservation form modal

### 2. Reservation Form Modal
Initial Fields (when creating reservation):
- Customer Name (required)
- Customer Email
- Customer Phone
- Eigenkapital (amount or percentage)
- 90/10 Deal checkbox
- Adjusted purchase price (if 90/10)
- External commission
- Internal commission
- Preferred notary (Notarwunsch) - optional
- Notes

Additional Fields (when status = 7 Notartermin):
- Notary appointment date (required)
- Notary appointment time (required)
- Notary location/address

### 3. Reservation Status Workflow Component
- Visual stepper showing current status
- Action buttons based on permissions
- Status history timeline

### 4. Reservations List Page
- Filterable table with all reservations
- Role-based visibility
- Quick status change actions
- Export functionality

## Investagon Sync Integration

### Sync Logic
1. Map Investagon status values to our reservation states
2. Create/update reservations when syncing properties
3. Preserve existing reservation data when possible
4. Log all sync operations

### Field Mapping
- Investagon customer data → reservation customer fields
- Investagon status → reservation status
- Financial details from Investagon → reservation financial fields

## Business Rules

### Reservation Fee Payment
1. When transitioning from status 5 (Angefragt) to 6 (Reserviert):
   - Property Manager/Tenant Admin MUST set `reservation_fee_paid = true`
   - System should record `reservation_fee_paid_date` automatically
   - This field cannot be set by Sales People
   - Frontend should show a checkbox/confirmation for fee payment

2. Waitlist Prioritization:
   - Reservations with `reservation_fee_paid = true` should be highlighted
   - When managing waitlist, paid reservations are preferred candidates for promotion

### Notary Appointment Validation
1. When transitioning from status 9 to 7 (Notartermin):
   - `notary_appointment_date` must be provided and in the future
   - `notary_appointment_time` must be provided
   - System should validate these fields before allowing the transition

2. Notary preference (Notarwunsch):
   - Can be set when creating the reservation
   - Can be updated at any time before status 0 (Verkauft)
   - Optional field - empty means no preference

### Property Status Sync
1. Only the active reservation controls property.active status
2. When active reservation changes status, property.active updates immediately
3. Waitlist reservations do not affect property status
4. When promoting from waitlist, property status updates to match new active reservation

### Visibility Rules
1. Sales People: Can only see their own reservations
2. Location Managers: Can see all reservations from their team members
3. Property Managers/Tenant Admins: Can see all reservations system-wide

## Implementation Plan

### Phase 1: Backend Foundation
1. Create database migrations
2. Implement reservation models
3. Create reservation service with state machine
4. Add API endpoints
5. Update property service for status sync

### Phase 2: Frontend Basic Features
1. Add reservation button to property detail
2. Create reservation form component
3. Implement reservations list page
4. Add basic status change functionality

### Phase 3: Advanced Features
1. Implement workflow visualization
2. Add status history view
3. Create team-based filtering
4. Add email notifications

### Phase 4: Integration
1. Implement Investagon sync
2. Add audit trail UI
3. Create reporting features
4. Performance optimization