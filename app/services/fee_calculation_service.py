"""
Fee Calculation Service

Handles calculation of notary and Grundbuch fees based on GNotKG Table B
and tenant-specific configuration.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.business import FeeTableB, TenantFeeConfig, Property
from app.schemas.business import (
    TenantFeeConfigCreate, TenantFeeConfigUpdate, TenantFeeConfigResponse,
    FeeCalculationRequest, FeeCalculationResponse
)
from app.core.exceptions import AppException, ValidationError


class FeeCalculationService:
    """Service for fee calculations and configuration"""
    
    VAT_RATE = Decimal('0.19')  # 19% VAT for notary services
    
    @staticmethod
    def get_tenant_fee_config(db: Session, tenant_id: UUID) -> Optional[TenantFeeConfig]:
        """Get fee configuration for a tenant"""
        result = db.execute(
            select(TenantFeeConfig).where(TenantFeeConfig.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    def create_tenant_fee_config(
        db: Session,
        tenant_id: UUID,
        data: TenantFeeConfigCreate,
        created_by: UUID
    ) -> TenantFeeConfig:
        """Create fee configuration for a tenant"""
        # Check if config already exists
        existing = FeeCalculationService.get_tenant_fee_config(db, tenant_id)
        if existing:
            raise ValidationError("Fee configuration already exists for this tenant")
        
        config = TenantFeeConfig(
            tenant_id=tenant_id,
            notary_kaufvertrag_rate=Decimal(str(data.notary_kaufvertrag_rate)),
            notary_grundschuld_rate=Decimal(str(data.notary_grundschuld_rate)),
            notary_vollzug_rate=Decimal(str(data.notary_vollzug_rate)),
            grundbuch_auflassung_rate=Decimal(str(data.grundbuch_auflassung_rate)),
            grundbuch_eigentum_rate=Decimal(str(data.grundbuch_eigentum_rate)),
            grundbuch_grundschuld_rate=Decimal(str(data.grundbuch_grundschuld_rate)),
            notary_override_percentage=Decimal(str(data.notary_override_percentage)) if data.notary_override_percentage else None,
            created_by=created_by,
            updated_by=created_by
        )
        
        db.add(config)
        db.commit()
        db.refresh(config)
        
        return config
    
    @staticmethod
    def update_tenant_fee_config(
        db: Session,
        tenant_id: UUID,
        data: TenantFeeConfigUpdate,
        updated_by: UUID
    ) -> TenantFeeConfig:
        """Update fee configuration for a tenant"""
        config = FeeCalculationService.get_tenant_fee_config(db, tenant_id)
        if not config:
            raise AppException("Fee configuration not found for this tenant", status_code=404)
        
        # Update fields if provided
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(config, field, Decimal(str(value)))
        
        config.updated_by = updated_by
        
        db.commit()
        db.refresh(config)
        
        return config
    
    @staticmethod
    def get_fee_from_table_b(db: Session, geschaeftswert: Decimal) -> Decimal:
        """Get fee from Table B based on business value"""
        # Query for the appropriate fee entry
        result = db.execute(
            select(FeeTableB).where(
                FeeTableB.geschaeftswert_from <= geschaeftswert,
                (FeeTableB.geschaeftswert_to >= geschaeftswert) | (FeeTableB.geschaeftswert_to.is_(None))
            ).order_by(FeeTableB.geschaeftswert_from.desc()).limit(1)
        )
        
        fee_entry = result.scalar_one_or_none()
        if not fee_entry:
            raise ValidationError(f"No fee entry found for business value {geschaeftswert}")
        
        # Handle values above 60 million
        if geschaeftswert > Decimal('60000000'):
            # Base fee for 60M
            base_fee = fee_entry.gebuehr
            # Add 165,000 per additional 50M
            excess = geschaeftswert - Decimal('60000000')
            additional_blocks = excess / Decimal('50000000')
            # Round up to next block
            additional_blocks = additional_blocks.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            additional_fee = additional_blocks * Decimal('165000')
            return base_fee + additional_fee
        
        return fee_entry.gebuehr
    
    @staticmethod
    def calculate_fees(
        db: Session,
        tenant_id: UUID,
        request: FeeCalculationRequest,
        property_id: Optional[UUID] = None
    ) -> FeeCalculationResponse:
        """Calculate notary and Grundbuch fees"""
        # Get tenant configuration
        config = FeeCalculationService.get_tenant_fee_config(db, tenant_id)
        if not config:
            # Create default configuration if not exists
            default_data = TenantFeeConfigCreate(
                notary_kaufvertrag_rate=2.0,
                notary_grundschuld_rate=1.0,
                notary_vollzug_rate=0.5,
                grundbuch_auflassung_rate=0.5,
                grundbuch_eigentum_rate=1.0,
                grundbuch_grundschuld_rate=1.0
            )
            config = FeeCalculationService.create_tenant_fee_config(
                db, tenant_id, default_data, tenant_id  # Use tenant_id as created_by for default
            )
        
        # Calculate purchase price after Werkvertrag
        purchase_price = Decimal(str(request.purchase_price))
        werkvertrag_amount = Decimal(str(request.werkvertrag_amount)) if request.has_werkvertrag and request.werkvertrag_amount else Decimal('0')
        purchase_price_after_werkvertrag = purchase_price - werkvertrag_amount
        loan_amount = Decimal(str(request.loan_amount))
        
        # Check for property-level override
        property_override = None
        if property_id:
            result = db.execute(
                select(Property.notary_override_percentage).where(Property.id == property_id)
            )
            property_override = result.scalar_one_or_none()
        
        # Use property override if available, otherwise tenant override
        override_percentage = None
        if request.property_notary_override is not None:
            override_percentage = Decimal(str(request.property_notary_override))
        elif property_override is not None:
            override_percentage = property_override
        elif config.notary_override_percentage is not None:
            override_percentage = config.notary_override_percentage
        
        # Calculate notary fees
        notary_fees = {}
        notary_subtotal = Decimal('0')
        
        # 1. Kaufvertrag Beurkundung
        kaufvertrag_geschaeftswert = purchase_price_after_werkvertrag
        kaufvertrag_base_fee = FeeCalculationService.get_fee_from_table_b(db, kaufvertrag_geschaeftswert)
        kaufvertrag_fee = kaufvertrag_base_fee * config.notary_kaufvertrag_rate
        notary_fees['kaufvertrag'] = {
            'geschaeftswert': float(kaufvertrag_geschaeftswert),
            'rate': float(config.notary_kaufvertrag_rate),
            'base_fee': float(kaufvertrag_base_fee),
            'calculated_fee': float(kaufvertrag_fee)
        }
        notary_subtotal += kaufvertrag_fee
        
        # 2. Grundschuld Beurkundung
        if loan_amount > 0:
            grundschuld_base_fee = FeeCalculationService.get_fee_from_table_b(db, loan_amount)
            grundschuld_fee = grundschuld_base_fee * config.notary_grundschuld_rate
            notary_fees['grundschuld'] = {
                'geschaeftswert': float(loan_amount),
                'rate': float(config.notary_grundschuld_rate),
                'base_fee': float(grundschuld_base_fee),
                'calculated_fee': float(grundschuld_fee)
            }
            notary_subtotal += grundschuld_fee
        
        # 3. Vollzug/Betreuung
        vollzug_geschaeftswert = purchase_price
        vollzug_base_fee = FeeCalculationService.get_fee_from_table_b(db, vollzug_geschaeftswert)
        vollzug_fee = vollzug_base_fee * config.notary_vollzug_rate
        notary_fees['vollzug'] = {
            'geschaeftswert': float(vollzug_geschaeftswert),
            'rate': float(config.notary_vollzug_rate),
            'base_fee': float(vollzug_base_fee),
            'calculated_fee': float(vollzug_fee)
        }
        notary_subtotal += vollzug_fee
        
        # Apply VAT to notary fees
        notary_vat = notary_subtotal * FeeCalculationService.VAT_RATE
        notary_total = notary_subtotal + notary_vat
        
        # Store original before override
        original_notary_total = notary_total
        override_applied = False
        
        # Apply override if set
        if override_percentage is not None:
            notary_total = purchase_price * (override_percentage / Decimal('100'))
            override_applied = True
        
        # Calculate Grundbuch fees (no VAT, no override)
        grundbuch_fees = {}
        grundbuch_total = Decimal('0')
        
        # 1. Auflassungsvormerkung
        auflassung_geschaeftswert = purchase_price
        auflassung_base_fee = FeeCalculationService.get_fee_from_table_b(db, auflassung_geschaeftswert)
        auflassung_fee = auflassung_base_fee * config.grundbuch_auflassung_rate
        grundbuch_fees['auflassung'] = {
            'geschaeftswert': float(auflassung_geschaeftswert),
            'rate': float(config.grundbuch_auflassung_rate),
            'base_fee': float(auflassung_base_fee),
            'calculated_fee': float(auflassung_fee)
        }
        grundbuch_total += auflassung_fee
        
        # 2. Eigentumsumschreibung
        eigentum_geschaeftswert = purchase_price
        eigentum_base_fee = FeeCalculationService.get_fee_from_table_b(db, eigentum_geschaeftswert)
        eigentum_fee = eigentum_base_fee * config.grundbuch_eigentum_rate
        grundbuch_fees['eigentum'] = {
            'geschaeftswert': float(eigentum_geschaeftswert),
            'rate': float(config.grundbuch_eigentum_rate),
            'base_fee': float(eigentum_base_fee),
            'calculated_fee': float(eigentum_fee)
        }
        grundbuch_total += eigentum_fee
        
        # 3. Eintragung der Grundschuld
        if loan_amount > 0:
            grundschuld_geschaeftswert = loan_amount
            grundschuld_base_fee = FeeCalculationService.get_fee_from_table_b(db, grundschuld_geschaeftswert)
            grundschuld_gf_fee = grundschuld_base_fee * config.grundbuch_grundschuld_rate
            grundbuch_fees['grundschuld'] = {
                'geschaeftswert': float(grundschuld_geschaeftswert),
                'rate': float(config.grundbuch_grundschuld_rate),
                'base_fee': float(grundschuld_base_fee),
                'calculated_fee': float(grundschuld_gf_fee)
            }
            grundbuch_total += grundschuld_gf_fee
        
        # Calculate total
        total_fees = notary_total + grundbuch_total
        
        return FeeCalculationResponse(
            purchase_price=float(purchase_price),
            purchase_price_after_werkvertrag=float(purchase_price_after_werkvertrag),
            loan_amount=float(loan_amount),
            notary_fees=notary_fees,
            notary_fees_subtotal=float(notary_subtotal),
            notary_fees_vat=float(notary_vat),
            notary_fees_total=float(notary_total),
            grundbuch_fees=grundbuch_fees,
            grundbuch_fees_total=float(grundbuch_total),
            total_fees=float(total_fees),
            override_applied=override_applied,
            override_percentage=float(override_percentage) if override_percentage else None,
            original_notary_total=float(original_notary_total) if override_applied else None
        )