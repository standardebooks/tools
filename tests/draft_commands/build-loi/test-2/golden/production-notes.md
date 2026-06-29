• Volumes 9 and 10 (appendix and Pepysiana) of the original series have been omitted from the production due to time constraints.
• Each diary entry has a time element to start. The datetime attribute is ISO8601 compliant (Gregorian), but the actual dates Pepys uses are Julian, so they don’t appear to match. This is correct.
• This date is copied into the `entry-x` id attribute for each diary entry. Unfortunately, this causes linting to fail with leading 0 errors, so we remove those for the id.
