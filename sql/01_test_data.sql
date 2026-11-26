-- =============================================================
-- 01_test_data.sql
-- Fake data for checking the calculations and queries before
-- real data arrives. Every company, drug, and trial is made up.
--
-- Safe to run again: rows that already exist are skipped.
-- Then run 02_calculations.sql,
-- then 03_queries.sql and 04_tests.sql.
-- Never run this on the real database.
-- =============================================================

USE biotech_catalyst;


-- -------------------------------------------------------------
-- Companies
--   Acme Bio and Beta Therapeutics: small, one drug each
--   Gamma Pharma: bigger, three drugs
-- -------------------------------------------------------------
INSERT IGNORE INTO companies (company_id, name, cik) VALUES
  (1, 'Acme Bio',          '0000000001'),
  (2, 'Beta Therapeutics', '0000000002'),
  (3, 'Gamma Pharma',      '0000000003');

INSERT IGNORE INTO company_aliases (alias_name, company_id, source) VALUES
  ('Acme Bio',              1, 'manual'),
  ('Acme Biosciences Inc.', 1, 'clinicaltrials'),
  ('Beta Therapeutics',     2, 'manual'),
  ('Gamma Pharma',          3, 'manual'),
  ('Gamma Pharmaceuticals', 3, 'clinicaltrials');


-- -------------------------------------------------------------
-- Stocks we track, plus XBI (the biotech sector, no company)
-- -------------------------------------------------------------
INSERT IGNORE INTO securities (security_id, ticker, company_id, type) VALUES
  (1, 'ACME', 1,    'stock'),
  (2, 'BETA', 2,    'stock'),
  (3, 'XBI',  NULL, 'etf'),
  (4, 'GAMA', 3,    'stock');


-- -------------------------------------------------------------
-- Daily prices, March 7-14, 2024
-- March 9 and 10 are a weekend, so they have no prices.
-- ACME has no prices after March 12 (tests the "missing price" case).
-- -------------------------------------------------------------
INSERT IGNORE INTO prices (security_id, trade_date, close, adjusted_close, volume) VALUES
  -- ACME
  (1, '2024-03-07', 21.50, 21.50, 1000000),
  (1, '2024-03-08', 21.88, 21.88, 1100000),   -- Friday
  (1, '2024-03-11', 24.50, 24.50, 3200000),   -- Monday: approval
  (1, '2024-03-12', 24.10, 24.10, 1500000),
  -- BETA
  (2, '2024-03-08', 41.00, 41.00,  800000),
  (2, '2024-03-11', 40.00, 40.00,  900000),
  (2, '2024-03-12', 22.00, 22.00, 5400000),   -- rejection
  -- XBI
  (3, '2024-03-07', 89.80, 89.80, 8000000),
  (3, '2024-03-08', 90.30, 90.30, 8200000),
  (3, '2024-03-11', 92.10, 92.10, 8500000),
  (3, '2024-03-12', 91.20, 91.20, 8100000),
  (3, '2024-03-13', 91.65, 91.65, 7900000),
  (3, '2024-03-14', 90.75, 90.75, 8300000),
  -- GAMA
  (4, '2024-03-08', 50.00, 50.00, 2000000),
  (4, '2024-03-11', 50.50, 50.50, 2100000),
  (4, '2024-03-12', 51.00, 51.00, 2600000),   -- approval
  (4, '2024-03-13', 51.20, 51.20, 2300000),   -- second approval
  (4, '2024-03-14', 47.00, 47.00, 4800000);   -- failed trial


-- -------------------------------------------------------------
-- Drugs, diseases, and trials
-- -------------------------------------------------------------
INSERT IGNORE INTO drugs (drug_id, brand_name, active_ingredient) VALUES
  (1, 'Acmezumab', 'acmezumab'),
  (2, 'Betaglip',  'betagliptin'),
  (3, 'Gammanib',  'gammanib'),
  (4, NULL,        'GX-204'),          -- still in trials, no brand name
  (5, 'Gammavir',  'gammavir');

INSERT IGNORE INTO conditions (condition_id, condition_name) VALUES
  (1, 'Non-small cell lung cancer'),
  (2, 'Type 2 diabetes'),
  (3, 'Hepatitis B');

INSERT IGNORE INTO trials (nct_number, company_id, phase, status, enrollment, start_date, completion_date) VALUES
  ('NCT00000001', 1, 'PHASE3', 'COMPLETED', 600, '2021-01-15', '2023-11-30'),
  ('NCT00000002', 2, 'PHASE3', 'COMPLETED', 900, '2020-06-01', '2023-06-30'),
  ('NCT00000003', 3, 'PHASE3', 'COMPLETED', 750, '2020-09-01', '2023-08-31'),
  ('NCT00000004', 3, 'PHASE2', 'COMPLETED', 220, '2022-02-01', '2024-01-31'),
  ('NCT00000005', 3, 'PHASE3', 'COMPLETED', 500, '2021-03-01', '2023-10-31');

INSERT IGNORE INTO trial_conditions (nct_number, condition_id) VALUES
  ('NCT00000001', 1),
  ('NCT00000002', 2),
  ('NCT00000003', 1),
  ('NCT00000004', 2),
  ('NCT00000005', 3);

INSERT IGNORE INTO trial_drugs (nct_number, drug_id) VALUES
  ('NCT00000001', 1),
  ('NCT00000002', 2),
  ('NCT00000003', 3),
  ('NCT00000004', 4),
  ('NCT00000005', 5);


-- -------------------------------------------------------------
-- FDA approvals
-- (Beta's rejection isn't here: rejections usually come from
--  press releases, not openFDA.)
-- -------------------------------------------------------------
INSERT IGNORE INTO fda_actions (fda_action_id, application_number, company_id, drug_id,
                         submission_type, status, action_date) VALUES
  (1, 'BLA000001', 1, 1, 'ORIG', 'AP', '2024-03-11'),
  (3, 'NDA000003', 3, 3, 'ORIG', 'AP', '2024-03-12'),
  (4, 'NDA000004', 3, 5, 'ORIG', 'AP', '2024-03-13');


-- -------------------------------------------------------------
-- Events (times are in UTC)
-- -------------------------------------------------------------
INSERT IGNORE INTO events (event_id, company_id, event_type, outcome, event_timestamp,
                    trading_day, nct_number, fda_action_id, accession_number, source_url) VALUES

  -- 1. Acme's drug approved on a Monday (Monday compares to Friday)
  (1, 1, 'fda_decision',  'approved', '2024-03-11 12:30:00', '2024-03-11',
   NULL, 1, NULL, NULL),

  -- 2. Beta's drug rejected, known only from a press release
  (2, 2, 'fda_decision',  'rejected', '2024-03-12 11:00:00', '2024-03-12',
   NULL, NULL, NULL, 'https://example.com/beta-press-release'),

  -- 3. Acme trial result on a day with no ACME price (should be flagged)
  (3, 1, 'trial_readout', 'positive', '2024-03-13 12:00:00', '2024-03-13',
   'NCT00000001', NULL, NULL, 'https://example.com/acme-readout'),

  -- 4. Gamma's Gammanib approved
  (4, 3, 'fda_decision',  'approved', '2024-03-12 12:00:00', '2024-03-12',
   NULL, 3, NULL, NULL),

  -- 5. Gamma's Phase 2 trial failed
  (5, 3, 'trial_readout', 'negative', '2024-03-14 11:30:00', '2024-03-14',
   'NCT00000004', NULL, NULL, 'https://example.com/gamma-readout'),

  -- 6. Gamma's Gammavir approved
  (6, 3, 'fda_decision',  'approved', '2024-03-13 12:00:00', '2024-03-13',
   NULL, 4, NULL, NULL);


-- -------------------------------------------------------------
-- Expected abnormal returns (stock's move - XBI's move):
--   1  Acme approved      11.97 - 1.99    =   9.98%
--   2  Beta rejected     -45.00 - (-0.98) = -44.02%
--   3  Acme readout       missing price
--   4  Gamma approved      0.99 - (-0.98) =   1.97%
--   5  Gamma failed trial -8.20 - (-0.98) =  -7.22%
--   6  Gamma approved      0.39 - 0.49    =  -0.10%
-- -------------------------------------------------------------
