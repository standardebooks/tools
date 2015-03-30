#Setting up your build environment

1.	Download and install Calibre: http://calibre-ebook.com/download

	**Important:** Don't use the version of Calibre included with your system's package manager.  That's almost always an out-of-date version that will cause problems.  Install it by downloading it directly from the Calibre website.
	
2.	Download and install epubcheck: https://github.com/IDPF/epubcheck/releases
	
	Currently you have to place it in /opt/epubcheck/.

3.	Install other dependencies.  On Ubuntu 15.04, you can do:
		
		sudo apt-add-repository ppa:svg-cleaner-team/svgcleaner
		sudo apt-get install xsltproc libxml2-utils xmlstarlet libxml-xpath-perl svgcleaner recode html-xml-utils
		sudo pip install roman titlecase beautifulsoup4
		
That should be it!
