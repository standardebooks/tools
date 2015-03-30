<?php

//We do this to work around a PHP bug, see http://php.net/manual/en/simplexmlelement.xpath.php#96153
$contents = file_get_contents($argv[1]);
$string = str_replace('xmlns=', 'ns=', $contents);

$xml = new SimpleXMLElement($string);

$newEndnotes = '';

$result = $xml->xpath("//li[@epub:type=\"rearnote\" or @epub:type=\"footnote\"]");

foreach($result as $note){
	$refLinks = $note->xpath("p[last()]/a[last()]");
	$refLink = '';
	$noteNumber = 0;
	$id = (string)$note->attributes()->id;
	if(sizeof($refLinks) > 0){
		$refLink = $refLinks[0]->asXml();
		$noteNumber =(string)$note->attributes()->{"data-se-note-number"};
	}
	else{
		die("Can't find ref link for: " . var_dump($note));
	}
	
	$newRefLink = preg_replace('/>.*?<\/a>/ius', '>' . $noteNumber . '</a>. ', $refLink);
	
	$noteText = $note->asXml();
	
	//Remove the root li node
	$noteText = trim(preg_replace('/^<li[^>]*?>(.*)<\/li>$/ius', '\1', $noteText));
	
	//Insert our new ref link
	$count = 0;
	$noteText = preg_replace('/^<p>/ius', '<p id="' . $id . '">' . $newRefLink, $noteText, -1, $count);
	
	//Make sure we actually replaced a <p>, sometimes a note can start with <blockquote>
	if($count == 0){
		$noteText = '<p id="' . $id . '">' . $newRefLink . '</p>' . $noteText;
	}
	
	//Remove our old ref link
	$noteText = str_replace($refLink, '', $noteText);
	
	//Trim trailing spaces left over after removing the ref link
	$noteText = str_replace(' </p>', '</p>', $noteText);
	
	//Sometimes ref links are in their own p tag--remove that too
	$noteText = preg_replace('/<p>\s*<\/p>/ius', '', $noteText);
	
	$newEndnotes .= $noteText . "\n";
}

$contents = preg_replace('/<ol>.*<\/ol>/ius', $newEndnotes, $contents);

file_put_contents($argv[1], $contents);
?>
