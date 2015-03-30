# filename: titlecase.awk
#   author: Eric Pement - email: eric [dot] pement [at] moody [dot] edu
#  version: 1.22
#     date: 25 February 2004
# requires: GNU awk
#
# Purpose:
#   This is a function for taking a string in "ALL CAPS", "lowercase", or
#   "miXeD cAsE" and converting it to "Title Case", such as would be used
#   for book or chapter titles. It also works well for normalizing personal
#   names and street addresses. It keeps Roman numerals and special
#   abbreviations (like USA, LXX, NT, NY) in caps, but keeps articles,
#   conjunctions, and prepositions between words in lowercase. Names like
#   D'Arcy, O'Reilly, and McDonald are properly capitalized, as are
#   abbreviations like Ph.D. or D.Min. Obeys most style manual rules.
#
#   credit: This function was inspired by totitle.awk by M. Joshua Ryan,
#           which had a similar purpose but not enough exception handling.
#           I completely rewrote it, added debugging and other features.
#
# function: titlecase("CHANGE TO TITLE CASE") --> "Change to Title Case"
#
# Other Features:
#   titlecase() will compress whitespace if a second parameter is passed.
#   It is sufficient to use a positive number: titlecase(string,1)
#
#   Debugging/diagnostic output will be printed to stdout if "-v debug=1
#   is added as a command-line argument to gawk.
#
#   If reformatting a mailing list, add "-v state_abb=1" as a command-line
#   argument for 59 two-letter abbreviations accepted by the Postal Service.
#
#   This function tries to implement the "Title Case" constructs specified
#   in the APA Style Manual and the Chicago Manual of Style. Instead of
#   merely capitalizing the first letter of each word and setting
#   everything else in lowercase, this function implements the following
#   conditions:
#
#  - Conjunctions, articles, and prepositions are set lowercase, UNLESS they
#    are the first word of the string or the first word after a colon, a
#    question mark, or an exclamation point.
#  - Compass points (NE, SW, etc.) are set in solid caps.
#  - Roman numerals (II, IV, VII, IX, etc.) are set in solid caps.
#  - Certain abbreviations are always capitalized (AIDS, ASCII, NT, USA, etc.)
#  - Names beginning with D' or O' are set as D'Arcy, O'Reilly, etc.
#  - Hyphenated strings receive internal caps (Smith-Williams, Twenty-Two)
#  - Contractions such as I'll, You've, Don't, etc. are handled properly
#  - Degrees such as Ph.D., M.Div., etc. are properly capitalized
#
# Sample Usage with GNU awk (gawk):
#
#   (1) Simple use. To change each line of "infile" and redirect the result
#   to "outfile", do this:
#
#   awk -f titlecase.awk -W source="{print titlecase($0)}" infile >outfile
#
#   (2) Complex use. To alter particular fields or substrings, use a
#   separate awk script. Below is a sample of using 2 scripts from a
#   command prompt under Microsoft Windows:
#
#   --------------------------------------------------------------
#   [c:\tmp]type infile
#   JOHN DOE,123 MAIN ST.,CHICAGO,IL,12345
#   OLD MACDONALD,456 FARM HWY.,PEORIA,IL,23456
#   TIM O'REILLY,P.O. BOX 789,LOS ANGELES,CA,34567
#
#   [c:\tmp]type myfile.awk
#   {
#      # Set the input field separator on the command line!
#      OFS = ","            # Set the output field separator
#      $1 = titlecase($1)   # Format the 1st field and
#      $2 = titlecase($2)   #   the 2nd field also.
#      print                # Print the revised line.
#   }
#
#   [c:\tmp]awk -F"," -f titlecase.awk -f myfile.awk infile
#   John Doe,123 Main St.,CHICAGO,IL,12345
#   Old MacDonald,456 Farm Hwy.,PEORIA,IL,23456
#   Tim O'Reilly,P.O. Box 789,LOS ANGELES,CA,34567
#   --------------------------------------------------------------
#
# Availability of GNU awk:
#   gawk for windows: http://gnuwin32.sourceforge.net/packages/gawk.htm
#   general links:    http://dmoz.org/Computers/Programming/Languages/Awk/
#
# CHANGELOG:
# 1.22 - Added a new switch to accept all 2-letter abbreviations of US States
#   and territories. Added "nor" to conjunctions; DVD, FM and TV to other.
#   More remarks throughout for new awk users.
# 1.21 - explicitly declared a field separator for split() function

BEGIN {

  #-----ABBREVIATIONS TO BE SET IN LOWERCASE-----
  articles     = "a an the "

  # AND, OR, NOR, and XOR must be manually inspected if the titles may be
  # discussing Boolean logic operations.
  conjunctions = "and but for nor or so "

  # Prepositions
  # Note: This list will not be perfect, since some prepositions require
  # grammatical analysis which is beyond the capacity of this script. In
  # typical title formats (e.g., MLA Style), adverbs are capitalized
  # while prepositions are not capitalized. Thus, "Do It Over, Jimmy"
  # (adverb), but "I Leap over the Wall" (preposition).
  #
  # If we omit from the list of "preps" words which can be both adverbs
  # and prepositions, then the words omitted will be capitalized and
  # the words included in the "preps" list will always be lowercased.
  #
  # Omitted: over (=finished), under, through, before, after
  preps = "against at between by in into of on to upon "

  # Build array of words to be set lowercased
  split(articles conjunctions preps, keep_lower, " ")

  #-----ABBREVIATIONS TO BE SET IN SOLID CAPS-----
  # Compass points
  # Omitted: NNE, ENE, ESE, SSE, SSW, WSW, WNW, NNW
  compass = "NE NW SE SW "

  # Religious references - add to only as needed
  religious = "OT NT LXX YHWH BC BCE AD CE MBI KJV ASV NIV NASB TEV RSV NRSV "

  # State names
  if (state_abb) {
    # All 50 states plus DC and USA
    states =        "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY "
    states = states "LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH "
    states = states "OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY USA "
    # Others below are: American Samoa, Federated States of Micronesia, Guam,
    # Marshall Islands, N. Mariana Islands, Palau, Puerto Rico, Virgin Islands
    states = states "AS FM GU MH MP PW PR VI "
  } else {
    # If not formatting a mailing list, do not add abbreviations which may
    # be whole English words (as, hi, in, oh, ok, me) or part of hyphenated
    # words (al-, co-, de-) ... unless you know your input very well. The
    # following is a minimal, conservative approach:
    states = "AZ CA CT DC IL MD MI ND NV NJ NY SD TX UT VT WY USA "
  }

  # Other abbreviations - add to this list as needed
  other =       "AIDS ASCII CD DHTML DNA DVD FBI GNU GPL IBM IRS ISBN ISSN "
  other = other "PHP ROM SSN TV FM "

  # build array of words to keep uppercase
  split(compass religious states other, keep_upper, " ")

}

function titlecase(string,x)  {

  # Initialize variables
  a = "";            # a is/will be the string ALREADY converted
  b = string;        # b is the rest of the string, so that (string = a b)
  compress = x;      # optional compression argument

  if (compress) {    # Compress spaces or tabs if 2nd argument passed
    gsub(/[ \t]+/, " ", b)
    if (debug) print "DIAG: Compress argument passed to function call"
  }

  b = toupper(b)     # Capitalize everything for ease of matching

  do {
    hit = 0;         # Initialize for later use

    # pos is the position of the NEXT punctuation mark (except apostrophe)
    # after the current word. If this is the last word in b, pos will be 0.
    # match() automatically sets RLENGTH
    pos = match(b, /[^A-Z']+/)

    if (pos > 0)    word = substr(b, 1, pos + RLENGTH - 1)
    else            word = b

    # 1st char of current word
    head = substr(b, 1, 1)

    # tail of current word
    if (pos > 0)    tail = substr(b, 2, pos + RLENGTH - 2)
    else            tail = substr(b, 2)

    # shorten the rest of the string
    b = substr(b, pos + RLENGTH  )

    #----Words to keep uppercase----
    # Case 1: abbreviations from the keep_upper array.
    for (var in keep_upper) {
      hit = match(word, "^" keep_upper[var] "\\>")
      if ( hit > 0 ) {
        if (debug)
          print "DIAG: Match UC on [" keep_upper[var] "] in string [" word "]";
	break;
      }
    }

    # Case 2: Roman numerals
    # Note: this match cannot distinguish between LIV (54 in Roman numerals)
    # and a personal name like "Liv Ullman".  The Roman numerals C (100),
    # D (500), and M (1000) are omitted to avoid false matches on words like
    # civil, did, dim, lid, mid-, mild, Vic, etc. Most uses of Roman numerals
    # in titles stays in the lower ranges, such as "Vol. II" or "Pt. XXIV".
    if ( hit == 0 && match(word, /^[IVXL]+\>/) ) {
      hit = 1
      # But we can undo I'd, I'll, I'm, I've and Ill.
      if (match(word,/^I'|ILL\>/)) hit = 0
      if (debug && hit == 1)
        print "DIAG: Match on Roman numerals in [" word "]"
    }

    #----Words to be set in MiXed case----
    # Case 3: Names like D'Arcy or O'Reilly
    if ( hit == 0 && match(word, /^[DO]'[A-Z]/) ) {
       if (debug) print "DIAG: Match on mixed case: " word
       word = substr(word,1,3) tolower(substr(word,4))
       hit = 1
    }

    # Case 4: Names like MacNeil or McDonald
    if ( hit == 0 && match(word,/^MA?C[B-DF-HJ-NP-TV-Z]/) ) {
      if (debug)
        print  "DIAG: Match on MacX: " substr(word,1,1) "-" \
        tolower(substr(word,2,RLENGTH-2)) "-" substr(word,RLENGTH,1) "-" \
        tolower(substr(word,RLENGTH+1))
      word = substr(word,1,1)       tolower(substr(word,2,RLENGTH-2)) \
             substr(word,RLENGTH,1) tolower(substr(word,RLENGTH+1))
      hit = 1
    }

    #----Words to set in lowercase----
    # Case 5: articles, conjunctions, prepositions from the keep_lower array
    if (hit == 0) {
      for (var2 in keep_lower) {
	hit = sub("^" toupper(keep_lower[var2]) "\\>", keep_lower[var2], word);
        if ( hit > 0 ) {
          if (debug)
            print "DIAG: Match LC on [" keep_lower[var2] "] in string [" word "]";
	  break;
        }
      }
    }

    #----Default: Capitalize everything else normally----
    if (hit > 0)    a = a word
    else            a = a toupper(head) tolower(tail)

  } while (pos > 0);

  # Everything should be converted now.

  # Double exception 1: Set 1st word of string in Cap case
  # Need to handle potential internal single/double quotes like
  #  "A Day in the Life" or 'On the Waterfront'
  match(a, /[A-Za-z]/)
  a = toupper(substr(a,1,RSTART)) substr(a,RSTART+1)

  # Double exception 2: Set 1st word after a colon, question mark or
  # exclamation point in title case. This kludge handles multiple colons,
  # question marks, etc. on the line. \a is the BEL or CTRL-G character.
  done = gensub(/([:?!][^a-zA-Z]*)([a-zA-Z])/,"\\1\a\\2", "g", a)

  while (match(done,/\a/)) {
    beg = substr(done,1,RSTART-1)
    cap = toupper(substr(done,RSTART+1,1))
    end = substr(done,RSTART+2)
    done = beg cap end
  }
  
  return done
}
#---end of awk script---
