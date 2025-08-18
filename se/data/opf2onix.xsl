<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet
	version="1.0"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
	xmlns:opf="http://www.idpf.org/2007/opf"
	xmlns:dc="http://purl.org/dc/elements/1.1/"
	exclude-result-prefixes="opf dc">

	<!-- Default values -->
	<xsl:param name="defaultContributorRole" select="'A01'"/> <!-- A01 = Author -->

	<!-- Helper functions -->
	<xsl:variable name="packageLang" select="normalize-space(/opf:package/opf:metadata/dc:language)"/>

	<xsl:variable name="primaryLang">
		<xsl:choose>
			<xsl:when test="contains($packageLang, '-')">
				<xsl:value-of select="substring-before($packageLang, '-')"/>
			</xsl:when>
			<xsl:when test="$packageLang">
				<xsl:value-of select="$packageLang"/>
			</xsl:when>
		</xsl:choose>
	</xsl:variable>

	<xsl:variable name="countryCode">
		<xsl:choose>
			<xsl:when test="contains($packageLang, '-')">
				<xsl:value-of select="substring-after($packageLang, '-')"/>
			</xsl:when>
		</xsl:choose>
	</xsl:variable>

	<xsl:template name="lang-to-iso639">
		<xsl:param name="lang"/>
		<xsl:choose>
			<xsl:when test="$lang='en'">eng</xsl:when>
			<xsl:otherwise><xsl:value-of select="$lang"/></xsl:otherwise>
		</xsl:choose>
	</xsl:template>

	<xsl:template name="marc-to-onix-role">
		<xsl:param name="marc"/>
		<xsl:choose>
			<xsl:when test="$marc='aut'">A01</xsl:when>
			<xsl:otherwise><xsl:value-of select="$defaultContributorRole"/></xsl:otherwise>
		</xsl:choose>
	</xsl:template>

	<!-- Key to find `<meta>` by `@refines` -->
	<xsl:key name="meta-by-refines" match="opf:meta" use="@refines"/>

	<!-- Rightmost-comma split for OPF `file-as` -->
	<xsl:template name="after-last-comma-raw">
		<xsl:param name="s"/>
		<xsl:choose>
			<xsl:when test="contains($s, ',')">
				<xsl:variable name="tail" select="substring-after($s, ',')"/>
				<xsl:choose>
					<xsl:when test="contains($tail, ',')">
						<xsl:call-template name="after-last-comma-raw">
							<xsl:with-param name="s" select="$tail"/>
						</xsl:call-template>
					</xsl:when>
					<xsl:otherwise>
						<xsl:value-of select="$tail"/>
					</xsl:otherwise>
				</xsl:choose>
			</xsl:when>
		</xsl:choose>
	</xsl:template>

	<xsl:template name="before-last-comma-raw">
		<xsl:param name="s"/>
		<xsl:variable name="tailRaw">
			<xsl:call-template name="after-last-comma-raw">
				<xsl:with-param name="s" select="$s"/>
			</xsl:call-template>
		</xsl:variable>
		<xsl:choose>
			<xsl:when test="string-length($tailRaw) &gt; 0">
				<xsl:value-of select="substring-before($s, concat(',', $tailRaw))"/>
			</xsl:when>
		</xsl:choose>
	</xsl:template>

	<!-- Title split driven by OPF `file-as` -->
	<xsl:template name="title-split-from-fileas" xmlns="http://ns.editeur.org/onix/3.1/reference">
		<xsl:param name="title"/>
		<xsl:param name="fileas"/>

		<!-- Normalize for comparisons -->
		<xsl:variable name="ti" select="normalize-space($title)"/>
		<xsl:variable name="fa" select="normalize-space($fileas)"/>
		<xsl:variable name="tiLower" select="translate($ti, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')"/>
		<xsl:variable name="faLower" select="translate($fa, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')"/>


		<xsl:choose>
			<!-- 1) If title and file-as are effectively identical, do NOT split -->
			<xsl:when test="$tiLower = $faLower">
				<NoPrefix/>
				<TitleWithoutPrefix textcase="02">
					<xsl:value-of select="$ti"/>
				</TitleWithoutPrefix>
			</xsl:when>

			<!-- 2) Else, attempt rightmost-comma split, but only use it if it reconstructs the title -->
			<xsl:when test="contains($fa, ',')">
				<!-- raw tail/head keeping original spacing, then normalize -->
				<xsl:variable name="tailRaw">
					<xsl:call-template name="after-last-comma-raw">
						<xsl:with-param name="s" select="$fileas"/> <!-- keep original spacing -->
					</xsl:call-template>
				</xsl:variable>
				<xsl:variable name="headRaw">
					<xsl:call-template name="before-last-comma-raw">
						<xsl:with-param name="s" select="$fileas"/>
					</xsl:call-template>
				</xsl:variable>

				<xsl:variable name="prefix" select="normalize-space($tailRaw)"/>
				<xsl:variable name="core"   select="normalize-space($headRaw)"/>

				<!-- Reconstruct both plausible human-title forms -->
				<xsl:variable name="recon1" select="concat($prefix, ' ', $core)"/>
				<xsl:variable name="recon2" select="concat($core, ', ', $prefix)"/>

				<xsl:variable name="recon1Lower" select="translate($recon1, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')"/>
				<xsl:variable name="recon2Lower" select="translate($recon2, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')"/>

				<xsl:choose>
					<!-- Only split if the reconstructed title matches the actual title -->
					<xsl:when test="$tiLower = $recon1Lower or $tiLower = $recon2Lower">
						<xsl:if test="string-length($prefix) &gt; 0">
							<TitlePrefix textcase="02">
								<xsl:value-of select="$prefix"/>
							</TitlePrefix>
						</xsl:if>
						<TitleWithoutPrefix textcase="02">
							<xsl:value-of select="$core"/>
						</TitleWithoutPrefix>
					</xsl:when>

					<!-- Otherwise, don't split (e.g., 'Winesburg, Ohio') -->
					<xsl:otherwise>
						<NoPrefix/>
						<TitleWithoutPrefix textcase="02">
							<xsl:value-of select="$ti"/>
						</TitleWithoutPrefix>
					</xsl:otherwise>
				</xsl:choose>
			</xsl:when>

			<!-- 3) No comma in `file-as`: don't split -->
			<xsl:otherwise>
				<NoPrefix/>
				<TitleWithoutPrefix textcase="02"><xsl:value-of select="$ti"/></TitleWithoutPrefix>
			</xsl:otherwise>
		</xsl:choose>
	</xsl:template>

	<xsl:output method="xml" indent="yes" encoding="utf-8"/>

	<xsl:template match="/opf:package">
		<!-- Title and associated metadata -->
		<xsl:variable name="url" select="normalize-space(opf:metadata/dc:identifier[@id='uid'])"/>
		<xsl:variable name="filename" select="translate(substring-after($url, 'https://standardebooks.org/ebooks/'), '/', '_')"/> <!-- Remove `https://standardebooks.org/ebooks/` from the identifier, and replace `/` with `_` -->
		<xsl:variable name="titleNode" select="opf:metadata/dc:title[1]"/>
		<xsl:variable name="titleText" select="normalize-space($titleNode)"/>
		<xsl:variable name="titleId" select="concat('#', $titleNode/@id)"/>
		<xsl:variable name="titleFileAs" select="normalize-space(key('meta-by-refines', $titleId)[@property='file-as'][1])"/>

		<!-- Subtitle -->
		<xsl:variable name="subtitle" select="normalize-space(opf:metadata/dc:title[key('meta-by-refines', concat('#', @id))[@property='title-type' andnormalize-space(.) = 'subtitle']][1])"/>

		<xsl:variable name="sentDate" select="translate(normalize-space(opf:metadata/opf:meta[@property='dcterms:modified']), '-:', '')"/>

		<!-- Start actual output -->
		<ONIXMessage xmlns="http://ns.editeur.org/onix/3.1/reference" release="3.1">
			<Header>
				<Sender>
					<SenderName>
						<xsl:value-of select="normalize-space(opf:metadata/dc:publisher)"/>
					</SenderName>
				</Sender>
				<SentDateTime><xsl:value-of select="$sentDate"/></SentDateTime>
			</Header>

			<Product datestamp="{$sentDate}"> <!-- `@datestamp` indicates when this record was updated -->
				<RecordReference>
					<xsl:value-of select="$url"/>
				</RecordReference>
				<NotificationType>03</NotificationType> <!-- 03 = Update -->

				<ProductIdentifier>
					<ProductIDType>22</ProductIDType> <!-- 22 = URN -->
					<IDValue>
						<xsl:value-of select="$url"/>
					</IDValue>
				</ProductIdentifier>

				<DescriptiveDetail>
					<ProductComposition>00</ProductComposition><!-- 00 = Single-component retail product -->
					<ProductForm>EB</ProductForm> <!-- EB = Digital download and online -->
					<ProductFormDetail>E101</ProductFormDetail> <!-- E101 = EPUB -->

					<xsl:if test="opf:metadata/opf:meta[@property='dcterms:conformsTo' and contains(., 'EPUB Accessibility 1.1')]">
						<ProductFormFeature>
							<ProductFormFeatureType>09</ProductFormFeatureType> <!-- 09 = E-publication accessibility detail -->
							<ProductFormFeatureValue>04</ProductFormFeatureValue> <!-- 04 = Compliant with ePub Accessibility Spec v1.1 -->
						</ProductFormFeature>
					</xsl:if>

					<ProductFormFeature>
						<ProductFormFeatureType>09</ProductFormFeatureType> <!-- 09 = E-publication accessibility detail -->
						<ProductFormFeatureValue>10</ProductFormFeatureValue><!-- 10 = No reading system accessibility options disabled -->
					</ProductFormFeature>

					<xsl:if test="opf:metadata/opf:meta[@property='schema:accessibilityFeature' and text() = 'tableOfContents']">
						<ProductFormFeature>
							<ProductFormFeatureType>09</ProductFormFeatureType> <!-- 09 = E-publication accessibility detail -->
							<ProductFormFeatureValue>11</ProductFormFeatureValue><!-- 11 = Table of contents navigation -->
						</ProductFormFeature>
					</xsl:if>

					<xsl:if test="opf:metadata/opf:meta[@property='schema:accessibilityFeature' and text() = 'readingOrder']">
						<ProductFormFeature>
							<ProductFormFeatureType>09</ProductFormFeatureType> <!-- 09 = E-publication accessibility detail -->
							<ProductFormFeatureValue>13</ProductFormFeatureValue><!-- 13 = Reading order -->
						</ProductFormFeature>
					</xsl:if>

					<xsl:if test="opf:metadata/opf:meta[@property='schema:accessibilityFeature' and text() = 'alternativeText']">
						<ProductFormFeature>
							<ProductFormFeatureType>09</ProductFormFeatureType> <!-- 09 = E-publication accessibility detail -->
							<ProductFormFeatureValue>14</ProductFormFeatureValue><!-- 14 = Short alternative descriptions -->
						</ProductFormFeature>
					</xsl:if>

					<ProductFormFeature>
						<ProductFormFeatureType>09</ProductFormFeatureType> <!-- 09 = E-publication accessibility detail -->
						<ProductFormFeatureValue>22</ProductFormFeatureValue><!-- 22 = Language tagging provided -->
					</ProductFormFeature>

					<xsl:if test="opf:metadata/opf:meta[@property='schema:accessibilityFeature' and text() = 'alternativeText']">
						<ProductFormFeature>
							<ProductFormFeatureType>09</ProductFormFeatureType> <!-- 09 = E-publication accessibility detail -->
							<ProductFormFeatureValue>52</ProductFormFeatureValue><!-- 52 = All non-decorative content supports reading without sight -->
						</ProductFormFeature>
					</xsl:if>

					<xsl:if test="opf:metadata/opf:meta[@property='dcterms:conformsTo' and contains(., 'WCAG 2.2')]">
						<ProductFormFeature>
							<ProductFormFeatureType>09</ProductFormFeatureType> <!-- 09 = E-publication accessibility detail -->
							<ProductFormFeatureValue>82</ProductFormFeatureValue><!-- 82 = WCAG v2.2-->
						</ProductFormFeature>
					</xsl:if>

					<xsl:if test="opf:metadata/opf:meta[@property='dcterms:conformsTo' and contains(., 'Level AA')]">
						<ProductFormFeature>
							<ProductFormFeatureType>09</ProductFormFeatureType> <!-- 09 = E-publication accessibility detail -->
							<ProductFormFeatureValue>85</ProductFormFeatureValue> <!-- 85 = WCAG level AA -->
						</ProductFormFeature>
					</xsl:if>

					<xsl:if test="opf:metadata/dc:identifier[starts-with(., 'https://standardebooks.org/')]">
						<ProductFormFeature>
							<ProductFormFeatureType>09</ProductFormFeatureType> <!-- 09 = E-publication accessibility detail -->
							<ProductFormFeatureValue>96</ProductFormFeatureValue> <!-- 96 = Publisher’s web page for detailed accessibility information -->
							<ProductFormFeatureDescription>https://standardebooks.org/about/accessibility</ProductFormFeatureDescription>
						</ProductFormFeature>
						<ProductFormFeature>
							<ProductFormFeatureType>09</ProductFormFeatureType> <!-- 09 = E-publication accessibility detail -->
							<ProductFormFeatureValue>99</ProductFormFeatureValue> <!-- 99 = Publisher contact for further accessibility information -->
							<ProductFormFeatureDescription>https://standardebooks.org/about#editor-in-chief</ProductFormFeatureDescription>
						</ProductFormFeature>
					</xsl:if>

					<ProductFormFeature>
						<ProductFormFeatureType>15</ProductFormFeatureType> <!-- 15 = E-publication format version code -->
						<ProductFormFeatureValue>101F</ProductFormFeatureValue> <!-- 101F = EPUB 3.3 -->
					</ProductFormFeature>

					<!-- If this book has MathML, add the accessibility feature -->
					<xsl:if test="opf:metadata/opf:meta[@property='schema:accessibilityFeature' and (text() = 'describedMath' or text() = 'MathML')]">
						<ProductFormFeature>
							<ProductFormFeatureType>09</ProductFormFeatureType> <!-- 09 = E-publication accessibility detail -->
							<ProductFormFeatureValue>17</ProductFormFeatureValue> <!-- 17 = Accessible math content as MathML -->
						</ProductFormFeature>
					</xsl:if>

					<!-- Title -->
					<TitleDetail>
						<TitleType>01</TitleType> <!-- 01 = Distinctive title (book); Cover title (serial); Title of content item, collection, or resource -->
						<TitleElement>
							<SequenceNumber>1</SequenceNumber>
							<TitleElementLevel>01</TitleElementLevel> <!-- 01 = Product -->

							<!-- Compute `Prefix` and `WithoutPrefix` from OPF `file-as` -->
							<xsl:call-template name="title-split-from-fileas">
								<xsl:with-param name="title" select="$titleText"/>
								<xsl:with-param name="fileas" select="$titleFileAs"/>
							</xsl:call-template>

							<!-- Subtitle, if present -->
							<xsl:if test="$subtitle">
								<Subtitle textcase="02"><xsl:value-of select="$subtitle"/></Subtitle>
							</xsl:if>
						</TitleElement>

						<TitleStatement>
							<xsl:value-of select="$titleText"/>
						</TitleStatement>
					</TitleDetail>

					<!-- Contributors -->
					<xsl:for-each select="opf:metadata/dc:creator">
						<Contributor>
							<SequenceNumber><xsl:value-of select="position()"/></SequenceNumber>
							<ContributorRole>
								<xsl:variable name="cid" select="concat('#', @id)"/>
								<xsl:variable name="marcRole" select="key('meta-by-refines', $cid)[@property='role'][1]"/>
								<xsl:choose>
									<xsl:when test="$marcRole">
										<xsl:call-template name="marc-to-onix-role">
											<xsl:with-param name="marc" select="$marcRole"/>
										</xsl:call-template>
									</xsl:when>
									<xsl:otherwise><xsl:value-of select="$defaultContributorRole"/></xsl:otherwise>
								</xsl:choose>
							</ContributorRole>
							<PersonName><xsl:value-of select="normalize-space(.)"/></PersonName>
							<xsl:variable name="ref" select="concat('#', @id)"/>
							<xsl:variable name="fileAs" select="key('meta-by-refines', $ref)[@property='file-as'][1]"/>
							<xsl:if test="$fileAs">
								<PersonNameInverted>
									<xsl:value-of select="$fileAs"/>
								</PersonNameInverted>
							</xsl:if>
						</Contributor>
					</xsl:for-each>

					<!-- Language -->
					<Language>
						<LanguageRole>01</LanguageRole> <!-- 01 = Language of text -->
						<LanguageCode>
							<xsl:call-template name="lang-to-iso639">
								<xsl:with-param name="lang" select="translate($primaryLang, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')"/>
							</xsl:call-template>
						</LanguageCode>
						<xsl:if test="$countryCode">
							<CountryCode><xsl:value-of select="$countryCode"/></CountryCode>
						</xsl:if>
					</Language>
				</DescriptiveDetail>
				<CollateralDetail>
					<SupportingResource>
						<ResourceContentType>01</ResourceContentType> <!-- 01 = Front cover -->
						<ContentAudience>00</ContentAudience> <!-- 00 = Unrestricted -->
						<ResourceMode>03</ResourceMode> <!-- 03 = Image -->
						<ResourceVersion>
							<ResourceForm>02</ResourceForm> <!-- 02 = Downloadable file -->
							<ResourceVersionFeature>
								<ResourceVersionFeatureType>01</ResourceVersionFeatureType> <!-- 01 = File format -->
								<FeatureValue>D502</FeatureValue> <!-- D502 = JPG -->
							</ResourceVersionFeature>
							<ResourceLink><xsl:value-of select="concat($url, '/downloads/cover.jpg')"/></ResourceLink>
						</ResourceVersion>
					</SupportingResource>
					<SupportingResource>
						<ResourceContentType>28</ResourceContentType> <!-- 01 = Full content -->
						<ContentAudience>00</ContentAudience> <!-- 00 = Unrestricted -->
						<ResourceMode>04</ResourceMode> <!-- 04 = Text -->
						<ResourceVersion>
							<ResourceForm>02</ResourceForm> <!-- 02 = Downloadable file -->
							<ResourceVersionFeature>
								<ResourceVersionFeatureType>01</ResourceVersionFeatureType> <!-- 01 = File format -->
								<FeatureValue>E101</FeatureValue> <!-- E101 = EPUB -->
								<FeatureNote>Recommended compatible epub</FeatureNote>
							</ResourceVersionFeature>
							<ResourceLink><xsl:value-of select="concat($url, '/downloads/', $filename, '.epub?source=feed')"/></ResourceLink>
						</ResourceVersion>
					</SupportingResource>
					<SupportingResource>
						<ResourceContentType>28</ResourceContentType> <!-- 01 = Full content -->
						<ContentAudience>00</ContentAudience> <!-- 00 = Unrestricted -->
						<ResourceMode>04</ResourceMode> <!-- 04 = Text -->
						<ResourceVersion>
							<ResourceForm>02</ResourceForm> <!-- 02 = Downloadable file -->
							<ResourceVersionFeature>
								<ResourceVersionFeatureType>01</ResourceVersionFeatureType> <!-- 01 = File format -->
								<FeatureValue>E101</FeatureValue> <!-- E101 = EPUB -->
								<FeatureNote>Advanced epub</FeatureNote>
							</ResourceVersionFeature>
							<ResourceLink><xsl:value-of select="concat($url, '/downloads/', $filename, '_advanced.epub?source=feed')"/></ResourceLink>
						</ResourceVersion>
					</SupportingResource>
					<SupportingResource>
						<ResourceContentType>28</ResourceContentType> <!-- 01 = Full content -->
						<ContentAudience>00</ContentAudience> <!-- 00 = Unrestricted -->
						<ResourceMode>04</ResourceMode> <!-- 04 = Text -->
						<ResourceVersion>
							<ResourceForm>02</ResourceForm> <!-- 02 = Downloadable file -->
							<ResourceVersionFeature>
								<ResourceVersionFeatureType>01</ResourceVersionFeatureType> <!-- 01 = File format -->
								<FeatureValue>E101</FeatureValue> <!-- E101 = EPUB -->
								<FeatureNote>Kobo Kepub epub</FeatureNote>
							</ResourceVersionFeature>
							<ResourceLink><xsl:value-of select="concat($url, '/downloads/', $filename, '.kepub.epub?source=feed')"/></ResourceLink>
						</ResourceVersion>
					</SupportingResource>
					<SupportingResource>
						<ResourceContentType>28</ResourceContentType> <!-- 01 = Full content -->
						<ContentAudience>00</ContentAudience> <!-- 00 = Unrestricted -->
						<ResourceMode>04</ResourceMode> <!-- 04 = Text -->
						<ResourceVersion>
							<ResourceForm>02</ResourceForm> <!-- 02 = Downloadable file -->
							<ResourceVersionFeature>
								<ResourceVersionFeatureType>01</ResourceVersionFeatureType> <!-- 01 = File format -->
								<FeatureValue>E116</FeatureValue> <!-- E101 = Amazon Kindle -->
								<FeatureNote>Amazon Kindle azw3</FeatureNote>
							</ResourceVersionFeature>
							<ResourceLink><xsl:value-of select="concat($url, '/downloads/', $filename, '.azw3?source=feed')"/></ResourceLink>
						</ResourceVersion>
					</SupportingResource>
					<SupportingResource>
						<ResourceContentType>28</ResourceContentType> <!-- 01 = Full content -->
						<ContentAudience>00</ContentAudience> <!-- 00 = Unrestricted -->
						<ResourceMode>04</ResourceMode> <!-- 04 = Text -->
						<ResourceVersion>
							<ResourceForm>02</ResourceForm> <!-- 02 = Downloadable file -->
							<ResourceVersionFeature>
								<ResourceVersionFeatureType>01</ResourceVersionFeatureType> <!-- 01 = File format -->
								<FeatureValue>E113</FeatureValue> <!-- E101 = XHTML -->
								<FeatureNote>XHTML</FeatureNote>
							</ResourceVersionFeature>
							<ResourceLink><xsl:value-of select="concat($url, '/text/single-page')"/></ResourceLink>
						</ResourceVersion>
					</SupportingResource>
				</CollateralDetail>
				<PublishingDetail>
					<Publisher>
						<PublishingRole>01</PublishingRole> <!-- 01 = Publisher -->
						<PublisherName>Standard Ebooks</PublisherName>
						<Website>
							<WebsiteRole>01</WebsiteRole> <!-- 01 = Publisher’s corporate website -->
							<WebsiteLink>https://standardebooks.org/</WebsiteLink>
						</Website>
					</Publisher>
					<PublishingDate>
						<PublishingDateRole>16</PublishingDateRole>  <!-- 16 = Last reissue date -->
						<Date><xsl:value-of select="$sentDate"/></Date>
					</PublishingDate>
				</PublishingDetail>
				<ProductSupply>
					<Market>
						<Territory>
							<CountriesIncluded>US</CountriesIncluded>
						</Territory>
					</Market>
				</ProductSupply>
			</Product>
		</ONIXMessage>
	</xsl:template>
</xsl:stylesheet>
