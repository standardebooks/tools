<?xml version="1.0" encoding="UTF-8"?>
<!--
Copyright (c) 2014 Matt Garrish

Permission is hereby granted, free of charge, to any person obtaining a copy of this software
and associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
-->
<!-- Via https://matt.garrish.ca/odds-n-ends/ncx-generator/ -->
<xsl:stylesheet
	xmlns="http://www.daisy.org/z3986/2005/ncx/"
	xmlns:xhtm="http://www.w3.org/1999/xhtml"
	xmlns:epub="http://www.idpf.org/2007/ops"
	xmlns:opf="http://www.idpf.org/2007/opf"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
	xmlns:dc="http://purl.org/dc/elements/1.1/"
	xmlns:c="urn:oasis:names:tc:opendocument:xmlns:container"
	version="2.0">

	<xsl:output omit-xml-declaration="no" encoding="UTF-8" indent="yes"/>

	<xsl:param name="cwd"/>

	<xsl:template match="xhtm:html">
		<xsl:element name="ncx">
			<xsl:namespace name="ncx">http://www.daisy.org/z3986/2005/ncx/</xsl:namespace>
			<xsl:attribute name="version">2005-1</xsl:attribute>
			<xsl:attribute name="xml:lang">
				<xsl:choose>
					<xsl:when test="@xml:lang"><xsl:value-of select="@xml:lang"/></xsl:when>
					<xsl:when test="@lang"><xsl:value-of select="@lang"/></xsl:when>
					<xsl:otherwise>??</xsl:otherwise>
				</xsl:choose>
			</xsl:attribute>

			<xsl:element name="head">
				<xsl:element name="meta">
					<xsl:attribute name="name">dtb:uid</xsl:attribute>
					<xsl:attribute name="content">
						<xsl:variable name="meta-inf" select="document(concat($cwd,'META-INF/container.xml'))"/>
						<xsl:variable name="package" select="document(concat($cwd,$meta-inf/c:container/c:rootfiles/c:rootfile[1]/@full-path))"/>
						<xsl:variable name="uid" select="$package/opf:package/@unique-identifier"/>
						<xsl:value-of select="$package/opf:package//dc:identifier[@id=$uid]"/>
					</xsl:attribute>
				</xsl:element>
			</xsl:element>

			<xsl:element name="docTitle">
				<xsl:element name="text">
					<xsl:value-of select="xhtm:head/xhtm:title"/>
				</xsl:element>
			</xsl:element>

			<xsl:if test="xhtm:head/xhtm:meta[@name='dc:author']">
				<xsl:for-each select="xhtm:head/xhtm:meta[@name='dc:author']">
					<xsl:element name="docAuthor">
						<xsl:element name="text">
							<xsl:value-of select="."/>
						</xsl:element>
					</xsl:element>
				</xsl:for-each>
			</xsl:if>

			<xsl:element name="navMap">
				<xsl:call-template name="addID"/>
				<xsl:apply-templates select="xhtm:body//xhtm:nav[@epub:type='toc']/xhtm:ol" mode="toc"/>
			</xsl:element>

			<xsl:if test="xhtm:body//xhtm:nav[@epub:type='page-list']">
				<xsl:element name="pageList">
					<xsl:call-template name="addID"/>
					<xsl:apply-templates select="xhtm:body//xhtm:nav[@epub:type='page-list']/xhtm:ol" mode="page-list"/>
				</xsl:element>
			</xsl:if>

			<!-- optional nav types that could be included -->

			<xsl:if test="xhtm:body//xhtm:nav[@epub:type='loi']">
				<xsl:element name="navList">
					<xsl:call-template name="addID"/>
					<xsl:attribute name="class">figure</xsl:attribute>
					<xsl:call-template name="addHeading">
						<xsl:with-param name="navType">loi</xsl:with-param>
					</xsl:call-template>
					<xsl:apply-templates select="xhtm:body/xhtm:nav[@epub:type='loi']/xhtm:ol" mode="flat"/>
				</xsl:element>
			</xsl:if>

			<xsl:if test="xhtm:body//xhtm:nav[@epub:type='lot']">
				<xsl:element name="navList">
					<xsl:call-template name="addID"/>
					<xsl:attribute name="class">table</xsl:attribute>
					<xsl:call-template name="addHeading">
						<xsl:with-param name="navType">lot</xsl:with-param>
					</xsl:call-template>
					<xsl:apply-templates select="xhtm:body/xhtm:nav[@epub:type='lot']/xhtm:ol" mode="flat"/>
				</xsl:element>
			</xsl:if>
		</xsl:element>
	</xsl:template>

	<xsl:template name="addID">
		<xsl:attribute name="id">
			<xsl:choose>
				<xsl:when test="@id">
					<xsl:value-of select="@id"/>
				</xsl:when>
				<xsl:otherwise>
					<xsl:value-of select="generate-id()"/>
				</xsl:otherwise>
			</xsl:choose>
		</xsl:attribute>
	</xsl:template>

	<xsl:template name="addHeading">
		<xsl:param name="navType" required="yes"/>
		<xsl:if test="xhtm:body//xhtm:nav[@epub:type=$navType]/xhtm:*[starts-with(local-name(.),'h')]">
			<xsl:element name="navInfo">
				<xsl:element name="text">
					<xsl:value-of select="xhtm:body/xhtm:nav[@epub:type=$navType]/xhtm:*[starts-with(local-name(.),'h')]/node()"/>
				</xsl:element>
			</xsl:element>
		</xsl:if>
	</xsl:template>

	<xsl:template match="xhtm:ol" mode="toc">
		<xsl:for-each select="xhtm:li">
			<xsl:choose>
				<xsl:when test="./xhtm:span">
					<xsl:comment>
						<xsl:value-of select="./xhtm:span[normalize-space()]"/>
					</xsl:comment>
					<xsl:apply-templates select="./xhtm:ol" mode="toc"/>
				</xsl:when>
				<xsl:otherwise>
					<xsl:element name="navPoint">
						<xsl:call-template name="addID"/>
						<xsl:element name="navLabel">
							<xsl:element name="text">
								<xsl:choose>
									<xsl:when test="@title">
										<xsl:value-of select="@title"/>
									</xsl:when>
									<xsl:otherwise>
										<xsl:value-of select="./xhtm:a[normalize-space()]"/>
									</xsl:otherwise>
								</xsl:choose>
							</xsl:element>
						</xsl:element>
						<xsl:element name="content">
							<xsl:attribute name="src">
								<xsl:value-of select="./xhtm:a/@href"/>
							</xsl:attribute>
						</xsl:element>
						<xsl:if test="./xhtm:ol">
							<xsl:apply-templates select="./xhtm:ol" mode="toc"/>
						</xsl:if>
					</xsl:element>
				</xsl:otherwise>
			</xsl:choose>
		</xsl:for-each>
	</xsl:template>

	<xsl:template match="xhtm:ol" mode="page-list">
		<xsl:for-each select="xhtm:li">
			<xsl:variable name="pageNumber" select="./xhtm:a[normalize-space()]"/>
			<xsl:element name="pageTarget">
				<xsl:attribute name="type">
					<xsl:choose>
					    <xsl:when test="@epub:type">
					        <xsl:choose>
					            <xsl:when test="@epub:type='frontmatter'">
					                <xsl:text>front</xsl:text>
					            </xsl:when>
					            <xsl:otherwise>
					                <xsl:text>normal</xsl:text>
					            </xsl:otherwise>
					        </xsl:choose>
					    </xsl:when>
					    <xsl:otherwise>
					        <xsl:choose>
					            <xsl:when test="matches($pageNumber,'[0-9]+')">
					                <!-- can't distinguish body from back in the nav doc -->
					                <xsl:text>normal</xsl:text>
					            </xsl:when>
					            <xsl:otherwise>
					                <!-- guess that non-numeric numbers are front -->
					                <xsl:text>front</xsl:text>
					            </xsl:otherwise>
					        </xsl:choose>
					    </xsl:otherwise>
					</xsl:choose>
				</xsl:attribute>
				<xsl:element name="navLabel">
					<xsl:element name="text">
						<xsl:value-of select="$pageNumber"/>
					</xsl:element>
				</xsl:element>
				<xsl:element name="content">
					<xsl:attribute name="src">
						<xsl:value-of select="./xhtm:a/@href"/>
					</xsl:attribute>
				</xsl:element>
			</xsl:element>
		</xsl:for-each>
	</xsl:template>

	<xsl:template match="xhtm:ol" mode="flat">
		<xsl:for-each select="xhtm:li">
			<xsl:element name="navTarget">
				<xsl:element name="navLabel">
					<xsl:element name="text">
						<xsl:value-of select="./xhtm:a[normalize-space()]"/>
					</xsl:element>
				</xsl:element>
				<xsl:element name="content">
					<xsl:attribute name="src">
						<xsl:value-of select="./xhtm:a/@href"/>
					</xsl:attribute>
				</xsl:element>
			</xsl:element>
		</xsl:for-each>
	</xsl:template>
</xsl:stylesheet>
