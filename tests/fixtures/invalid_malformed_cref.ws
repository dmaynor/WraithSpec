SENTINEL:7E99:(SID:malformed-test|MODE:design|PHASE:ideation|CRef:VA-P1@@2)

## Overview

This document has a malformed CRef (profile reference).

The CRef field contains "VA-P1@@2" which has a double @ symbol,
making it invalid according to the grammar specification.

Valid format should be: CRef:<profile_id>@<version>
Example: CRef:VA-P1@1

## Expected Behavior

The validator should:
1. Parse the SENTINEL header
2. Detect the malformed CRef field
3. Return NON_COMPLIANT status with a clear error message
