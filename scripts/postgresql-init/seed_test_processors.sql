-- ============================================================================
-- Seed Test Processors for Filtration Testing
-- ============================================================================
-- This script seeds organization_processors and underwriting_processors
-- to test different filtration scenarios:
--   1. Application Processor: enabled=true, auto=true (SHOULD BE SELECTED)
--   2. Stipulation Processor: enabled=true, auto=false (SHOULD NOT BE SELECTED - auto off)
--   3. Document Processor: enabled=false, auto=true (SHOULD NOT BE SELECTED - disabled)
-- ============================================================================

-- Get the test account ID (created_by/updated_by)
DO $$
DECLARE
    v_account_id UUID := '00000000-0000-0000-0000-000000000002';
    v_organization_id UUID := '00000000-0000-0000-0000-000000000001';
    v_underwriting_id UUID := 'e1b38421-6157-41d3-bd13-f2c2f74771b3';
    v_org_proc_app_id UUID;
    v_org_proc_stip_id UUID;
    v_org_proc_doc_id UUID;
BEGIN
    -- ========================================================================
    -- 1. Create Organization Processors (Purchased/Entitlements)
    -- ========================================================================
    
    RAISE NOTICE 'Creating organization processors...';
    
    -- Application Processor (should be selected)
    INSERT INTO organization_processors (
        id,
        organization_id,
        processor,
        name,
        auto,
        price_amount,
        price_unit,
        price_currency,
        purchased_by,
        purchased_at,
        status,
        config,
        notes,
        created_at,
        created_by,
        updated_at,
        updated_by
    ) VALUES (
        gen_random_uuid(),
        v_organization_id,
        'test_application_processor',
        'Test Application Processor',
        true,  -- auto enabled at org level
        100,   -- $1.00 per execution
        'execution',
        'USD',
        v_account_id,
        NOW(),
        'active',
        jsonb_build_object(
            'enabled', true,
            'description', 'Processes application form data',
            'processor_type', 'APPLICATION'
        ),
        'Test processor for application data',
        NOW(),
        v_account_id,
        NOW(),
        v_account_id
    ) RETURNING id INTO v_org_proc_app_id;
    
    RAISE NOTICE '  ✅ Created Application Processor: %', v_org_proc_app_id;
    
    -- Stipulation Processor (should NOT be selected - auto=false)
    INSERT INTO organization_processors (
        id,
        organization_id,
        processor,
        name,
        auto,
        price_amount,
        price_unit,
        price_currency,
        purchased_by,
        purchased_at,
        status,
        config,
        notes,
        created_at,
        created_by,
        updated_at,
        updated_by
    ) VALUES (
        gen_random_uuid(),
        v_organization_id,
        'test_bank_statement_processor',
        'Test Bank Statement Processor',
        false,  -- auto disabled - requires manual trigger
        250,    -- $2.50 per document
        'document',
        'USD',
        v_account_id,
        NOW(),
        'active',
        jsonb_build_object(
            'enabled', true,
            'description', 'Analyzes bank statements for revenue and NSF',
            'processor_type', 'STIPULATION',
            'stipulation_type', 's_bank_statement',
            'minimum_document', 3
        ),
        'Test processor for bank statements - requires manual execution',
        NOW(),
        v_account_id,
        NOW(),
        v_account_id
    ) RETURNING id INTO v_org_proc_stip_id;
    
    RAISE NOTICE '  ✅ Created Test Bank Statement Processor (auto=false): %', v_org_proc_stip_id;
    
    -- Document Processor (should NOT be selected - enabled=false)
    INSERT INTO organization_processors (
        id,
        organization_id,
        processor,
        name,
        auto,
        price_amount,
        price_unit,
        price_currency,
        purchased_by,
        purchased_at,
        status,
        config,
        notes,
        created_at,
        created_by,
        disabled_at,
        disabled_by,
        updated_at,
        updated_by
    ) VALUES (
        gen_random_uuid(),
        v_organization_id,
        'test_drivers_license_processor',
        'Test Drivers License Processor',
        true,   -- auto enabled but processor is disabled
        150,    -- $1.50 per document
        'document',
        'USD',
        v_account_id,
        NOW(),
        'disabled',  -- DISABLED
        jsonb_build_object(
            'enabled', false,
            'description', 'Verifies driver license documents',
            'processor_type', 'DOCUMENT',
            'stipulation_type', 's_drivers_license'
        ),
        'Test processor - DISABLED to test filtration',
        NOW(),
        v_account_id,
        NOW(),
        v_account_id,
        NOW(),
        v_account_id
    ) RETURNING id INTO v_org_proc_doc_id;
    
    RAISE NOTICE '  ✅ Created Test Drivers License Processor (disabled): %', v_org_proc_doc_id;
    
    -- ========================================================================
    -- 2. Create Underwriting Processors (Link to Underwriting)
    -- ========================================================================
    
    RAISE NOTICE '';
    RAISE NOTICE 'Creating underwriting processors for underwriting: %', v_underwriting_id;
    
    -- Application Processor - enabled and auto
    INSERT INTO underwriting_processors (
        id,
        organization_id,
        underwriting_id,
        organization_processor_id,
        current_executions_list,
        processor,
        name,
        auto,
        notes,
        enabled,
        config_override,
        effective_config,
        price_snapshot_amount,
        price_snapshot_unit,
        price_snapshot_currency,
        created_by,
        created_at,
        updated_at,
        updated_by
    ) VALUES (
        gen_random_uuid(),
        v_organization_id,
        v_underwriting_id,
        v_org_proc_app_id,
        ARRAY[]::UUID[],
        'test_application_processor',
        'Test Application Processor',
        true,  -- AUTO ENABLED
        'Should be selected by filtration',
        true,  -- ENABLED
        NULL,
        jsonb_build_object(
            'enabled', true,
            'processor_type', 'APPLICATION'
        ),
        100,
        'execution',
        'USD',
        v_account_id,
        NOW(),
        NOW(),
        v_account_id
    );
    
    RAISE NOTICE '  ✅ Linked Application Processor (enabled=true, auto=true)';
    
    -- Test Bank Statement Processor - enabled but auto=false
    INSERT INTO underwriting_processors (
        id,
        organization_id,
        underwriting_id,
        organization_processor_id,
        current_executions_list,
        processor,
        name,
        auto,
        notes,
        enabled,
        config_override,
        effective_config,
        price_snapshot_amount,
        price_snapshot_unit,
        price_snapshot_currency,
        created_by,
        created_at,
        updated_at,
        updated_by
    ) VALUES (
        gen_random_uuid(),
        v_organization_id,
        v_underwriting_id,
        v_org_proc_stip_id,
        ARRAY[]::UUID[],
        'test_bank_statement_processor',
        'Test Bank Statement Processor',
        false,  -- AUTO DISABLED
        'Should NOT be selected by filtration (auto=false)',
        true,   -- ENABLED
        NULL,
        jsonb_build_object(
            'enabled', true,
            'processor_type', 'STIPULATION',
            'stipulation_type', 's_bank_statement',
            'minimum_document', 3
        ),
        250,
        'document',
        'USD',
        v_account_id,
        NOW(),
        NOW(),
        v_account_id
    );
    
    RAISE NOTICE '  ✅ Linked Test Bank Statement Processor (enabled=true, auto=false)';
    
    -- Test Drivers License Processor - disabled
    INSERT INTO underwriting_processors (
        id,
        organization_id,
        underwriting_id,
        organization_processor_id,
        current_executions_list,
        processor,
        name,
        auto,
        notes,
        enabled,
        config_override,
        effective_config,
        price_snapshot_amount,
        price_snapshot_unit,
        price_snapshot_currency,
        created_by,
        created_at,
        disabled_at,
        disabled_by,
        updated_at,
        updated_by
    ) VALUES (
        gen_random_uuid(),
        v_organization_id,
        v_underwriting_id,
        v_org_proc_doc_id,
        ARRAY[]::UUID[],
        'test_drivers_license_processor',
        'Test Drivers License Processor',
        true,   -- AUTO ENABLED
        'Should NOT be selected by filtration (enabled=false)',
        false,  -- DISABLED
        NULL,
        jsonb_build_object(
            'enabled', false,
            'processor_type', 'DOCUMENT',
            'stipulation_type', 's_drivers_license'
        ),
        150,
        'document',
        'USD',
        v_account_id,
        NOW(),
        NOW(),
        v_account_id,
        NOW(),
        v_account_id
    );
    
    RAISE NOTICE '  ✅ Linked Test Drivers License Processor (enabled=false, auto=true)';
    
    -- ========================================================================
    -- Summary
    -- ========================================================================
    
    RAISE NOTICE '';
    RAISE NOTICE '========================================================================';
    RAISE NOTICE 'SEED COMPLETE - Test Processors Created';
    RAISE NOTICE '========================================================================';
    RAISE NOTICE 'Expected Filtration Behavior:';
    RAISE NOTICE '  ✅ Application Processor: SELECTED (enabled=true, auto=true)';
    RAISE NOTICE '  ❌ Test Bank Statement Processor: SKIPPED (auto=false)';
    RAISE NOTICE '  ❌ Test Drivers License Processor: SKIPPED (enabled=false)';
    RAISE NOTICE '========================================================================';
    
END $$;

