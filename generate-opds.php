<?

$contentFiles = explode("\n", trim(shell_exec("locate --regex \"/standardebooks.org/ebooks/.+content.opf\" | sort")));

print("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:schema="http://schema.org/">
	<id>https://standardebooks.org/opds/all</id>
	<link href="https://standardebooks.org/opds/all" rel="self" type="application/atom+xml;profile=opds-catalog;kind=acquisition"/>
	<link href="https://standardebooks.org/opds/" rel="start" type="application/atom+xml;profile=opds-catalog;kind=navigation"/>
	<title>All Standard Ebooks</title>
	<updated><?= gmdate('Y-m-d\TH:i:s\Z') ?></updated>
	<author>
		<name>Standard Ebooks</name>
		<uri>https://standardebooks.org</uri>
	</author>
	<? foreach($contentFiles as $path){ 
	if($path == '')
		continue;

	$xml = new SimpleXmlElement(str_replace('xmlns=', 'ns=', file_get_contents("$path")));
	$xml->registerXPathNamespace('dc', 'http://purl.org/dc/elements/1.1/');

	$authors = array();
	$url = preg_replace('/^url:/ius', '', array_shift($xml->xpath('/package/metadata/dc:identifier')));
	$relativeUrl = preg_replace('/^https:\/\/standardebooks.org/ius', '', $url);

	$title = array_shift($xml->xpath('/package/metadata/dc:title'));

	$description = array_shift($xml->xpath('/package/metadata/dc:description'));

	$tags = $xml->xpath('/package/metadata/meta[@property="se:subject"]');

	$authors = $xml->xpath('/package/metadata/dc:creator');

	$published = array_shift($xml->xpath('/package/metadata/dc:date'));

	$language = array_shift($xml->xpath('/package/metadata/dc:language'));

	$modified = array_shift($xml->xpath('/package/metadata/meta[@property="dcterms:modified"]'));

	$description = array_shift($xml->xpath('/package/metadata/dc:description'));

	$subjects = $xml->xpath('/package/metadata/dc:subject');

	$sources = $xml->xpath('/package/metadata/dc:source');

	$filesystemPath = preg_replace('/\/src\/epub\/content.opf$/ius', '', $path);
	$epubFilename = preg_replace('/(\.base|\.epub)/ius', '', preg_replace('/.+\//ius', '', array_shift(glob($filesystemPath . '/dist/*.epub'))));
	$mobiFilename = preg_replace('/.+\//ius', '', array_shift(glob($filesystemPath . '/dist/*.mobi')));

	?>
	<entry>
		<id><?= $url ?></id>
		<title><?= $title ?></title>
		<? foreach($authors as $author){
			$wikiUrl = array_shift($xml->xpath('/package/metadata/meta[@property="se:url.encyclopedia.wikipedia"][@refines="#' . $author->attributes()->id . '"]'));
			$fullName = array_shift($xml->xpath('/package/metadata/meta[@property="se:name.person.full-name"][@refines="#' . $author->attributes()->id . '"]'));
			$nacoafLink = array_shift($xml->xpath('/package/metadata/meta[@property="se:url.authority.nacoaf"][@refines="#' . $author->attributes()->id . '"]'));
		?>
		<author>
			<name><?= $author ?></name>
			<? if($wikiUrl !== null){ ?><uri><?= $wikiUrl ?></uri><? } ?>
			<? if($fullName !== null){ ?><schema:alternateName><?= $fullName ?></schema:alternateName><? } ?>
			<? if($nacoafLink !== null){ ?><schema:sameAs><?= $nacoafLink ?></schema:sameAs><? } ?>
		</author>
		<? } ?>
		<published><?= $published ?></published>
		<updated><?= $modified ?></updated>
		<dc:language><?= $language ?></dc:language>
		<dc:publisher>Standard Ebooks</dc:publisher>
		<? foreach($sources as $source){ ?>
		<dc:source><?= $source ?></dc:source>
		<? } ?>
		<rights>Public domain in the United States.</rights>
		<content type="text"><?= htmlentities($description) ?></content>
		<? foreach($subjects as $subject){ ?>
		<category scheme="http://purl.org/dc/terms/LCSH" term="<?= htmlentities($subject) ?>"/>
		<? } ?>
		<link href="<?= $relativeUrl ?>/src/epub/images/cover.svg" rel="http://opds-spec.org/image" type="image/svg+xml"/>
		<link href="<?= $relativeUrl ?>/dist/<?= $epubFilename ?>.epub" rel="http://opds-spec.org/acquisition/open-access" type="application/epub+zip"/>
		<link href="<?= $relativeUrl ?>/dist/<?= $epubFilename ?>.base.epub" rel="http://opds-spec.org/acquisition/open-access" type="application/epub+zip"/>
		<link href="<?= $relativeUrl ?>/dist/<?= $mobiFilename ?>" rel="http://opds-spec.org/acquisition/open-access" type="application/x-mobipocket-ebook"/>
	</entry>
	<? } ?>
</feed>
