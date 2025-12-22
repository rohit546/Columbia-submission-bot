# Columbia Automation - All Fields Documentation

This document lists all fields, dropdowns, and radio buttons filled during the Columbia Insurance automation process.

---

## 📋 **POLICY INFORMATION PAGE** (`/quote/generalInformation`)

### **Radio Buttons:**

1. **Is this a new venture?**
   - **Field Name:** `newVenture`
   - **Value:** `"No"` (hardcoded)
   - **Source:** Hardcoded (always "No")

### **Input Fields:**

2. **Effective Date**
   - **Field Name:** `effectiveDate`
   - **Format:** `mm/dd/yyyy`
   - **Value:** Current date + 1 day (auto-calculated)
   - **Source:** Auto-calculated on server, or from `quote_data['effective_date']`

3. **Person Entering Risk** (Contact Name)
   - **Field Name:** `personEnteringRisk`
   - **Value:** Contact name (e.g., "John Doe")
   - **Source:** `quote_data['person_entering_risk']` or `quote_data['contact_name']`

4. **Email of Person Entering Risk**
   - **Field Name:** `personEnteringRiskEmail`
   - **Value:** Email address (e.g., "john.doe@example.com")
   - **Source:** `quote_data['person_entering_risk_email']` or `quote_data['email']`

5. **Company Name**
   - **Field Name:** `insuredName.company`
   - **Value:** Company name (e.g., "Test Company LLC")
   - **Source:** `quote_data['company_name']` or `quote_data['business_name']`

6. **DBA (Optional)**
   - **Field Name:** `insuredName.dba`
   - **Value:** DBA name (e.g., "Test DBA")
   - **Source:** `quote_data['dba']` or `quote_data['dba_name']` (optional)

7. **Mailing Address**
   - **Field Name:** `address.fullAddress`
   - **Value:** Full address (e.g., "280 Griffin Street, McDonough, GA 30253")
   - **Source:** `quote_data['mailing_address']` or `quote_data['address']`
   - **Note:** Must select from autocomplete suggestions (first suggestion is selected)

### **Dropdowns:**

8. **Business Type**
   - **Field Name:** `businessType`
   - **Value:** `"LIMITED LIABILITY COMPANY"` (default)
   - **Source:** `quote_data['business_type']` (defaults to "LIMITED LIABILITY COMPANY")

---

## 📋 **SAFEGUARD/POLICY INFORMATION PAGE** (`/quote/safeguard/policyInformation`)

### **Dropdowns:**

9. **Business Type** (Safeguard)
   - **Field Name:** `sfg.businessType`
   - **Value:** `"Mercantile"` (hardcoded)
   - **Source:** Hardcoded (always "Mercantile")

---

## 📋 **LOCATION INFORMATION MODAL**

### **Buttons:**

10. **Address Same As Mailing**
    - **Field Name:** Button click
    - **Action:** Clicked automatically
    - **Source:** Hardcoded (always clicked)

### **Radio Buttons:**

11. **Protection Class**
    - **Field Name:** `protectionClass`
    - **Value:** Selected based on minimum number pattern (e.g., (01), (02), (03))
    - **Logic:** 
      - If single class → already selected (do nothing)
      - If multiple classes → select the one with minimum number pattern (never "x" patterns like (1x), (2x))
    - **Source:** Auto-selected based on address (not user input)

12. **Property Deductible Amount**
    - **Field Name:** `propertyDeductibleAmount`
    - **Value:** `"$2,500"` (hardcoded)
    - **Source:** Hardcoded (always "$2,500")

### **Dropdowns:**

13. **Wind/Hail Deductible**
    - **Field Name:** `windHailDeductible`
    - **Value:** `"$2,500"` (hardcoded)
    - **Source:** Hardcoded (always "$2,500")

### **Input Fields:**

14. **Gross Sales**
    - **Field Name:** `grossSales`
    - **Value:** `"100000"` (default)
    - **Source:** `quote_data['gross_sales']` or `quote_data['gross_sales_amount']` (defaults to "100000")

---

## 📋 **NEW BUILDING INFORMATION MODAL**

### **Radio Buttons:**

15. **Is this building an ancillary or secondary building?**
    - **Field Name:** `ancillaryBuilding` (various IDs)
    - **Value:** `"No"` (hardcoded)
    - **Source:** Hardcoded (always "No")
    - **Note:** May not always appear (conditional field)

16. **If the applicant is insuring the canopy is it listed as a separate building?**
    - **Field Name:** `separateCanopy`
    - **Value:** `"Yes"` (hardcoded)
    - **Source:** Hardcoded (always "Yes")

17. **Additional Interests**
    - **Field Name:** `additionalInsureds`
    - **Value:** `"No"` (hardcoded)
    - **Source:** Hardcoded (always "No")

18. **Applicant is**
    - **Field Name:** `ownerOccupied`
    - **Options:**
      - `"Tenant of the building"` (id: `ownerOccupied_N2`) - 3rd option
      - `"Owner and occupying over 90% of the building"` (id: `ownerOccupied_N1`) - 1st option
    - **Value:** Based on input
    - **Source:** `quote_data['applicant_is']` or `quote_data['applicant_type']`
    - **Logic:** 
      - If contains "tenant" → select 3rd option
      - If contains "owner" → select 1st option
      - Default: "tenant"

19. **Construction Type**
    - **Field Name:** `constructionType`
    - **Value:** `"Frame"` (1st option, id: `constructionType_01`) (hardcoded)
    - **Source:** Hardcoded (always "Frame")

20. **Roof Type**
    - **Field Name:** `roofType`
    - **Value:** `"Other"` (4th option, id: `roofType_Other`) (hardcoded)
    - **Source:** Hardcoded (always "Other")

21. **Sprinkler**
    - **Field Name:** `sprinkler`
    - **Value:** `"No"` (id: `sprinkler_N`) (hardcoded)
    - **Source:** Hardcoded (always "No")

22. **Building Valuation** (Only if applicant is "owner")
    - **Field Name:** `buildingValuation`
    - **Value:** `"Replacement Cost"` (1st option, id: `buildingValuation_1`) (hardcoded)
    - **Source:** Hardcoded (always "Replacement Cost")
    - **Conditional:** Only appears/filled when `applicant_is` is "owner"

23. **Earthquake Coverage**
    - **Field Name:** `earthquakeCoverage`
    - **Value:** `"No"` (id: `earthquakeCoverage_N`) (hardcoded)
    - **Source:** Hardcoded (always "No")

### **Dropdowns:**

24. **Class Code**
    - **Field Name:** `classCode` (search dropdown)
    - **Value:** `"09321"` (hardcoded)
    - **Source:** Hardcoded (always "09321")
    - **Note:** Type "09321" and press Enter to select

### **Input Fields:**

25. **Number Of Mortgagees/Loss Payees**
    - **Field Name:** `numberOfMortgageesLossPayees`
    - **Value:** `"0"` (hardcoded)
    - **Source:** Hardcoded (always "0")

26. **Original Construction Year**
    - **Field Name:** `constructionYear`
    - **Value:** Current year - 20 (auto-calculated, e.g., "2005")
    - **Source:** Auto-calculated, or from `quote_data['construction_year']` or `quote_data['original_construction_year']`

27. **Number of Stories**
    - **Field Name:** `numberOfStories`
    - **Value:** `"2"` (default)
    - **Source:** `quote_data['number_of_stories']` or `quote_data['stories']` (defaults to "2")

28. **Square Footage**
    - **Field Name:** `squareFootage`
    - **Value:** `"3500"` (default, must be above 3000)
    - **Source:** `quote_data['square_footage']` or `quote_data['square_feet']` (defaults to "3500")

29. **Building Limit** (Only if applicant is "owner")
    - **Field Name:** `buildingLimit`
    - **Value:** `"500000"` (default)
    - **Source:** `quote_data['building_limit']` or `quote_data['building_value']` (defaults to "500000")
    - **Conditional:** Only filled when `applicant_is` is "owner"

30. **Business Personal Property Limit**
    - **Field Name:** `bppLimit`
    - **Value:** `"70000"` (default)
    - **Source:** `quote_data['bpp_limit']` or `quote_data['business_personal_property_limit']` (defaults to "70000")

---

## 📊 **SUMMARY BY FIELD TYPE**

### **INPUT FIELDS (Text Inputs):**
1. Effective Date (`effectiveDate`) - Auto-calculated or from `quote_data['effective_date']`
2. Person Entering Risk (`personEnteringRisk`) - From `quote_data['person_entering_risk']` or `quote_data['contact_name']`
3. Email of Person Entering Risk (`personEnteringRiskEmail`) - From `quote_data['person_entering_risk_email']` or `quote_data['email']`
4. Company Name (`insuredName.company`) - From `quote_data['company_name']` or `quote_data['business_name']`
5. DBA (`insuredName.dba`) - From `quote_data['dba']` or `quote_data['dba_name']` (optional)
6. Mailing Address (`address.fullAddress`) - From `quote_data['mailing_address']` or `quote_data['address']`
7. Gross Sales (`grossSales`) - From `quote_data['gross_sales']` or `quote_data['gross_sales_amount']` (default: "100000")
8. Number Of Mortgagees/Loss Payees (`numberOfMortgageesLossPayees`) - Hardcoded: "0"
9. Original Construction Year (`constructionYear`) - Auto-calculated or from `quote_data['construction_year']`
10. Number of Stories (`numberOfStories`) - From `quote_data['number_of_stories']` or `quote_data['stories']` (default: "2")
11. Square Footage (`squareFootage`) - From `quote_data['square_footage']` or `quote_data['square_feet']` (default: "3500")
12. Building Limit (`buildingLimit`) - From `quote_data['building_limit']` or `quote_data['building_value']` (default: "500000") - **Only if owner**
13. Business Personal Property Limit (`bppLimit`) - From `quote_data['bpp_limit']` or `quote_data['business_personal_property_limit']` (default: "70000")

### **DROPDOWNS:**
1. Business Type (`businessType`) - From `quote_data['business_type']` (default: "LIMITED LIABILITY COMPANY")
2. Business Type - Safeguard (`sfg.businessType`) - Hardcoded: "Mercantile"
3. Wind/Hail Deductible (`windHailDeductible`) - Hardcoded: "$2,500"
4. Class Code (`classCode`) - Hardcoded: "09321"

### **RADIO BUTTONS:**
1. Is this a new venture? (`newVenture`) - Hardcoded: "No"
2. Protection Class (`protectionClass`) - Auto-selected based on address (minimum number pattern)
3. Property Deductible Amount (`propertyDeductibleAmount`) - Hardcoded: "$2,500"
4. Is this building an ancillary or secondary building? (`ancillaryBuilding`) - Hardcoded: "No" (conditional)
5. If the applicant is insuring the canopy is it listed as a separate building? (`separateCanopy`) - Hardcoded: "Yes"
6. Additional Interests (`additionalInsureds`) - Hardcoded: "No"
7. Applicant is (`ownerOccupied`) - From `quote_data['applicant_is']` or `quote_data['applicant_type']` (default: "tenant")
8. Construction Type (`constructionType`) - Hardcoded: "Frame"
9. Roof Type (`roofType`) - Hardcoded: "Other"
10. Sprinkler (`sprinkler`) - Hardcoded: "No"
11. Building Valuation (`buildingValuation`) - Hardcoded: "Replacement Cost" - **Only if owner**
12. Earthquake Coverage (`earthquakeCoverage`) - Hardcoded: "No"

---

## 🎯 **FIELDS TO ACCEPT FROM EXTERNAL SOURCE (User Input)**

Based on the analysis, here are the fields that should be accepted from external sources:

### **Required Fields:**
1. `person_entering_risk` (or `contact_name`) - Person Entering Risk
2. `person_entering_risk_email` (or `email`) - Email of Person Entering Risk
3. `company_name` (or `business_name`) - Company Name
4. `mailing_address` (or `address`) - Mailing Address

### **Optional Fields:**
5. `dba` (or `dba_name`) - DBA (Optional)
6. `effective_date` - Effective Date (if not provided, auto-calculated: current + 1 day)
7. `business_type` - Business Type (if not provided, defaults to "LIMITED LIABILITY COMPANY")
8. `applicant_is` (or `applicant_type`) - Applicant Type: "tenant" or "owner" (defaults to "tenant")
9. `gross_sales` (or `gross_sales_amount`) - Gross Sales (defaults to "100000")
10. `construction_year` (or `original_construction_year`) - Construction Year (if not provided, auto-calculated: current year - 20)
11. `number_of_stories` (or `stories`) - Number of Stories (defaults to "2")
12. `square_footage` (or `square_feet`) - Square Footage (defaults to "3500")
13. `building_limit` (or `building_value`) - Building Limit (defaults to "500000", only used if applicant is "owner")
14. `bpp_limit` (or `business_personal_property_limit`) - Business Personal Property Limit (defaults to "70000")

---

## 🔒 **HARDCODED FIELDS (Always Same)**

These fields are always set to the same value and don't need user input:

1. **Is this a new venture?** → "No"
2. **Business Type (Safeguard)** → "Mercantile"
3. **Property Deductible Amount** → "$2,500"
4. **Wind/Hail Deductible** → "$2,500"
5. **Is this building an ancillary or secondary building?** → "No"
6. **Class Code** → "09321"
7. **If the applicant is insuring the canopy is it listed as a separate building?** → "Yes"
8. **Number Of Mortgagees/Loss Payees** → "0"
9. **Additional Interests** → "No"
10. **Construction Type** → "Frame"
11. **Roof Type** → "Other"
12. **Sprinkler** → "No"
13. **Building Valuation** → "Replacement Cost" (only if owner)
14. **Earthquake Coverage** → "No"

---

## 📝 **EXAMPLE WEBHOOK PAYLOAD**

```json
{
  "action": "start_automation",
  "task_id": "optional_unique_id",
  "quote_data": {
    "person_entering_risk": "John Doe",
    "person_entering_risk_email": "john.doe@example.com",
    "company_name": "Test Company LLC",
    "dba": "Test DBA",
    "mailing_address": "280 Griffin Street, McDonough, GA 30253",
    "business_type": "LIMITED LIABILITY COMPANY",
    "applicant_is": "tenant",
    "gross_sales": "100000",
    "construction_year": "2005",
    "number_of_stories": "2",
    "square_footage": "3500",
    "bpp_limit": "70000"
  }
}
```

**Note:** Fields like `effective_date`, `business_type`, `gross_sales`, `construction_year`, `number_of_stories`, `square_footage`, and `bpp_limit` have defaults, so they're optional in the payload.

