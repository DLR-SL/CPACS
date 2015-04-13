<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:xs="http://www.w3.org/2001/XMLSchema"
  exclude-result-prefixes="xs"
  version="2.0">

<!-- XSLT 2.0 stylesheet by Wendell Piez, http://www.wendellpiez.com
     First version August 2011
     This version November 2012
     https://github.com/wendellpiez/XMLNamespaceFixup/blob/master/XSLT/namespace-cleanup.xsl -->
  
<!-- This stylesheet is released into the public domain.     
     Please credit your sources. -->
     
<!-- Run this stylesheet with a non-false value for $diagnostic
     if you want the output to present a comment with details on
     the renaming performed. -->
  <xsl:param name="diagnostic" select="false()"/>

<!-- 
  This stylesheet performs namespace normalization as follows:
  
  A set of controlled namespaces is stipulated (as a variable in
  the stylesheet). Each namespace is identified with its URI and
  assigned a prefix.
  
  Namespaces already in the source document are examined, with both
  URIs and prefixes noted by the stylesheet.
  
  These two lists are compared, and a list of namespaces is generated
  for the target document, including
  * Any namespaces from the control list set that are actually used,
    with the prefix assigned them in the control set.
  * All other namespaces used, with prefixes assigned to them ad-hoc:
    either the first prefix given to the same namespace in the source,
    if it does not conflict with any other prefix, or a prefix
    modified to avoid conflicts if it does.
  
  The result instance is a copy of the source instance, except:
  * Element and attribute names are all given with the prefixes
    assigned by the stylesheet (one prefix per namespace)
  * All namespace declarations needed are promoted to the top 
    level (where they have document scope).
  
  In the control set, a single namespace may be designated as a
  default; i.e., prefixes will not be assigned to elements and
  attributes in this namespace.
  
  Note, however, that this will prevent the stylesheet from processing 
  elements in no namespace, since they cannot be prefixed in the result 
  and namespace undeclarations that would permit them in are not
  permitted in the target specification. Use this option only if the
  usage of namespaces in the source is already well controlled.
  
  (Another stylesheet in this distribution can be used as a pre-process
  to cast elements in no namespace into a namespace, if this is
  helpful.)
  
  Note also:

  * If the source document has a default namespace (i.e. a namespace
    with a URI but no prefix), this namespace must be listed in the
    control (either as the default, or assigned a prefix), or like
    any other namespace used it will be assigned an arbitrary prefix.
    
  * If an error condition is detected by the stylesheet, it will
    copy the source to the result unchanged, with a comment saying so
    and noting the error(s). Error conditions include both the 
    situation just described (the control set designates a default 
    namespace and the source data contains elements in no namespace), 
    and also errors in the control set specification (such as
    duplicates of either prefixes or namespaces).
        
  -->

  <xsl:variable name="controlled-namespaces">
  <!-- $controlled-namespaces represents the set of namespaces we wish 
       to control in transforming the source document, reassigning prefixes
       where necessary while maintaining namespace bindings as given. -->
    
    <!--<ns default="yes" uri="whathaveyou"/>-->

    <!-- Set required="yes" if the result should declare the namespace
         even if it is never used in the document. -->
    <!-- Note that normalization will fail if the default (unprefixed)
         namespace is included in the spec, but the source document has
         elements not in a namespace! (since they can't be assigned 
         a prefix either). To prevent this, first run a namespace-binding
         stylesheet to cast unassigned elements into a namespace. -->
    <!-- EXAMPLE:
    <ns prefix="mml" uri="http://www.w3.org/1998/Math/MathML" required="yes"/>
    <ns prefix="xlink" uri="http://www.w3.org/1999/xlink" required="yes"/>
    <ns prefix="oasis" uri="http://docs.oasis-open.org/ns/oasis-exchange/table"/>
    <ns prefix="svg" uri="http://www.w3.org/2000/svg"/>
    -->
    <ns prefix="xsd" uri="http://www.w3.org/2001/XMLSchema" required="yes"/>
    <ns prefix="ddue" uri="http://ddue.schemas.microsoft.com/authoring/2003/5" required="yes"/>
    <ns prefix="html" uri="http://www.w3.org/1999/xhtml" required="yes"/>
    <ns prefix="sd" uri="http://schemas.xsddoc.codeplex.com/schemaDoc/2009/3" required="yes"/>
    <ns prefix="xlink" uri="http://www.w3.org/1999/xlink" required="yes"/>
  </xsl:variable>

 <xsl:variable name="extant-namespaces">
    <!-- $extant-namespaces represents all namespaces used in the document. -->
    <xsl:for-each-group select="//*|//@*" group-by="namespace-uri(.)">
      <!-- We select all elements and attributes in the document assigned to a namespace,
           grouping them by namespace URI; this leaves out namespaces declared but not used. -->
      <xsl:choose>
        <xsl:when test="current-grouping-key() (: excluding nodes not in a namespace :)">
          <ns uri="{current-grouping-key()}">
            <xsl:for-each-group select="current-group()" group-by="string(prefix-from-QName(node-name(.)))">
              <xsl:choose>
                <xsl:when test="current-grouping-key()">
                  <prefix>
                    <xsl:value-of select="current-grouping-key()"/>
                  </prefix>
                </xsl:when>
                <xsl:otherwise>
                  <default/>
                </xsl:otherwise>
              </xsl:choose>
            </xsl:for-each-group>
          </ns>
        </xsl:when>
        <xsl:otherwise>
          <!-- In this case, we have elements and attributes not in a namespace. -->
          <xsl:if test="current-group()/self::element()">
            <!-- If any of these are elements, we need to represent a null namespace,
                 since this will prevent us from representing a namespace without a
                 prefix. -->
            <ns null="yes"/>
          </xsl:if>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:for-each-group>
  </xsl:variable>

  <xsl:variable name="assigned-namespaces" as="element()+">
    <!-- $assigned-namespaces represents all the namespaces we may need, including
         all $controlled namespaces designated as required; any other 
         $controlled-namespaces extant, and any $extant-namespaces that 
         are not controlled. -->
    <!-- First we include the controlled namespaces that are required or extant, -->
    <xsl:copy-of select="$controlled-namespaces/ns[@uri=$extant-namespaces/ns/@uri or @required='yes']"/>
    <!-- and next any extant namespaces that are not explicitly controlled, -->
    <xsl:for-each select="$extant-namespaces/ns[not(@uri=$controlled-namespaces/ns/@uri)]">
      <!-- including its namespace URI (or null for no-namespace), -->
      <ns>
        <xsl:copy-of select="@uri | @null"/>
        <xsl:if test="exists(@uri)">
          <!-- and assigning it a prefix. -->
          <xsl:attribute name="prefix">
            <!-- If the source gives this namespace any prefixes that are not given
                 elsewhere either to a controlled namespace (whether appearing or not)
                 or to a different extant namespace appearing earlier, we use the
                 first available. -->
            <xsl:for-each
              select="prefix[not(.=$controlled-namespaces/ns/@prefix)
                  and not(.=current()/preceding-sibling::ns/prefix)][1]">
              <xsl:value-of select="."/>
            </xsl:for-each>
            <!-- Otherwise, we make a prefix by concatenating the first prefix used
                 for this namespace (or 'ns' if no prefix is ever used) with a numeral,
                 using the position of the extant namespace among all those listed, since
                 it will be unique to it. -->
            <xsl:if
              test="empty(prefix[not(.=$controlled-namespaces/ns/@prefix)
                      and not(.=current()/preceding-sibling::ns/prefix)][1])">
              <xsl:value-of select="prefix[1]"/>
              <xsl:if test="empty(prefix)">ns</xsl:if>
              <xsl:value-of select="position()"/>
            </xsl:if>
          </xsl:attribute>
        </xsl:if>
      </ns>
    </xsl:for-each>
  </xsl:variable>
  
  <xsl:variable name="errors">
    <!-- Generates a temporary tree containing reports of error conditions
         either in the specification given for controlled namespaces,
         or because the specs cannot be followed for this document
         (because a default namespace is specified and the
         document contains names in no namespace, making uprefixed
         names unavailable). -->
    <xsl:if test="exists($controlled-namespaces/ns[@default='yes'])">
      <xsl:choose>
        <xsl:when test="exists($controlled-namespaces/ns[@default='yes'][2])">
          <ERROR>
            <xsl:text>Can't declare more than one namespace</xsl:text>
            <xsl:text> as default="yes" in the control set.</xsl:text>
          </ERROR>
        </xsl:when>
        <xsl:when test="$extant-namespaces/ns/@null='yes' and exists(
          $extant-namespaces/ns[@uri=$controlled-namespaces/ns[@default='yes']/@uri])">
          <ERROR>
            <xsl:text>Can't assign namespace "</xsl:text>
            <xsl:value-of select="$controlled-namespaces/ns[@default='yes']/@uri"/>
            <xsl:text>" as the default (with no prefix) because elements exist</xsl:text>
            <xsl:text> in the source with no namespace (and so must be unprefixed).</xsl:text>
          </ERROR>
        </xsl:when>
      </xsl:choose>
    </xsl:if>
    <xsl:for-each select="$controlled-namespaces/ns
      [@uri = preceding-sibling::ns/@uri]">
      <ERROR>
        <xsl:text>Repeat declaration for namespace "</xsl:text>
        <xsl:value-of select="@uri"/>
        <xsl:text>" in the control set. </xsl:text>
      </ERROR>
    </xsl:for-each>
    <xsl:for-each select="$controlled-namespaces/ns
      [@prefix = preceding-sibling::ns/@prefix]">
      <ERROR>
        <xsl:text>Repeat assignment of prefix "</xsl:text>
        <xsl:value-of select="@prefix"/>
        <xsl:text>" in the control set. </xsl:text>
      </ERROR>
    </xsl:for-each>
  </xsl:variable>

  <!-- ============================================================ -->
  <!-- Processing the source document                               -->
  
  <xsl:template match="/">
    <xsl:text>&#xA;</xsl:text>
    <!-- If in diagnostic mode, we write a mapping report into the
         result. -->
    <xsl:apply-templates select=".[$diagnostic]" mode="mapping-report"/>
    <xsl:choose>
      <xsl:when test="exists($errors/node())">
        <!-- If there are errors, we report them, and copy the source
             as-is instead of messing with it. -->
        <xsl:apply-templates select="$errors" mode="report"/>
        <xsl:call-template name="error-notice"/> 
        <xsl:copy-of select="/"/>
      </xsl:when>
      <xsl:otherwise>
        <!-- Otherwise we proceed. -->
        <xsl:apply-templates/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  
  <xsl:template match="*">
    <!-- $ns represents the namespace for this element -->
    <xsl:variable name="ns"
      select="$assigned-namespaces
        [@uri=namespace-uri(current())]"/>
    <!-- We generate an element in the same namespace, with the 
         assigned prefix in its name. -->
    <xsl:element name="{string-join(($ns/@prefix,local-name()),':')}"
      namespace="{$ns/@uri}">
      <!-- Mode "ns-promote" sees to it that all assigned namespaces
           will be present everywhere. -->
      <xsl:apply-templates select="." mode="ns-promote"/>
      <xsl:apply-templates select="@*"/>
      <xsl:apply-templates select="node()"/>
    </xsl:element>
  </xsl:template>

  <xsl:template match="@*">
    <!-- $ns represents the namespace for this attribute -->
    <xsl:variable name="ns"
      select="$assigned-namespaces
        [@uri=namespace-uri(current())]"/>
    <!-- We generate an attribute in the same namespace, with the
         assigned prefix in its name. -->
    <xsl:attribute name="{string-join(($ns/@prefix,local-name()),':')}"
      namespace="{$ns/@uri}" select="."/>
  </xsl:template>

  <xsl:template match="/*" mode="ns-promote">
    <!-- Matching the document (root) element, we generate a namespace 
         node for each namespace assigned in the document. -->
    <xsl:for-each select="$assigned-namespaces[exists(@uri)]">
      <xsl:namespace name="{@prefix}" select="@uri"/>
    </xsl:for-each>
  </xsl:template>

  <!-- But we only have to generate namespace nodes at the top level,
       since namespaces will be inherited through the tree. -->
  <xsl:template match="*" mode="ns-promote"/>

  <!-- We copy comments and processing instructions unchanged. -->
  <xsl:template match="comment() | processing-instruction()">
    <xsl:copy-of select="."/>
  </xsl:template>
  
  <!-- ============================================================ -->
  <!-- Error reporting                                              -->
  
  <!-- If we can't proceed with tidying, we report why not. -->
  
  <xsl:template match="ERROR" mode="report">
    <!-- If diagnostic mode is on, we write a report into comments
         in the document. -->
    <xsl:if test="$diagnostic">
      <xsl:text>&#xA;</xsl:text>
      <xsl:comment>
        <xsl:text> ERROR: </xsl:text>
        <xsl:value-of select="."/>
        <xsl:text> </xsl:text>
      </xsl:comment>
    </xsl:if>
    <!-- In any case, we also generate a message. -->
    <xsl:message>
      <xsl:text>ERROR: </xsl:text>
      <xsl:value-of select="."/>
    </xsl:message>
  </xsl:template>

  <!-- If we couldn't clean up the namespaces, we write a comment 
       to say so. -->
  <xsl:template name="error-notice">
    <xsl:text>&#xA;</xsl:text>
    <xsl:comment> Namespaces are retained from source data. </xsl:comment>
    <xsl:text>&#xA;</xsl:text>
  </xsl:template>
  
  <!-- We have a variable available for diagnostics (not currently used). -->
  <xsl:variable name="ns-report">
    <NS-REPORT>
      <EXTANT>
        <xsl:copy-of select="$extant-namespaces"/>
      </EXTANT>
      <ASSIGNED>
        <xsl:copy-of select="$assigned-namespaces"/>
      </ASSIGNED>
    </NS-REPORT>
  </xsl:variable>

  <!-- For generating a report on how namespaces are to be mapped
       from source to result. -->
  <xsl:template match="node()" mode="mapping-report">
    <xsl:text>&#xA;</xsl:text>
    <xsl:comment>
      <xsl:text> Namespaces mapping from source </xsl:text>
      <xsl:value-of select="document-uri(/)"/>
      <xsl:text>: </xsl:text>
      <xsl:for-each select="$assigned-namespaces">
        <xsl:text>&#xA;        xmlns</xsl:text>
        <xsl:for-each select="@prefix">
          <xsl:text>:</xsl:text>
          <xsl:value-of select="."/>
        </xsl:for-each>
        <xsl:text>="</xsl:text>
        <xsl:value-of select="@uri"/>
        <xsl:text>" - prefixed in source: </xsl:text>
        <xsl:apply-templates mode="report"
          select="$extant-namespaces/ns[@uri=current()/@uri]/(prefix,default)"/>
      </xsl:for-each>
      <xsl:text> </xsl:text>
    </xsl:comment>
    <xsl:text>&#xA;</xsl:text>      
  </xsl:template>
  
  <!-- When generating the mapping report, we want namespace
       prefixes to be punctuated. -->
  <xsl:template mode="report" match="ns/prefix">
    <xsl:if test="position() gt 1">, </xsl:if>
    <xsl:text>'</xsl:text>
    <xsl:value-of select="."/>
    <xsl:text>'</xsl:text>
  </xsl:template>
  
  <xsl:template mode="report" match="ns/default">
    <xsl:if test="position() gt 1">, </xsl:if>
    <xsl:text>[none]</xsl:text>
  </xsl:template>
  
  <!-- ============================================================ -->
  <!-- End stylesheet                                               -->
  <!-- ============================================================ -->

</xsl:stylesheet>