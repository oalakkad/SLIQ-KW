"use client";

import { useMenuCategories } from "@/hooks/use-menu-categories";
import {
  Box,
  Text,
  VStack,
  SimpleGrid,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Link,
  useMediaQuery,
  IconButton,
  HStack,
} from "@chakra-ui/react";
import { useAppSelector } from "@/redux/hooks";
import NextLink from "next/link";
import { FaInstagram } from "react-icons/fa";
import { useSiteSettings } from "@/hooks/use-site-settings";

const Footer = () => {
  const { data: categories = [] } = useMenuCategories();
  const [isMobile] = useMediaQuery("(max-width: 950px)");
  const isArabic = useAppSelector((state) => state.lang.isArabic);
  const { data: siteSettings } = useSiteSettings();

  const brandName = siteSettings?.brand_name || "SLIQ";
  const instagramUrl = siteSettings?.instagram_url || "https://www.instagram.com/sliq.hair/";

  const socials = [
    { icon: <FaInstagram />, href: instagramUrl },
  ];

  const headingFont = isArabic
    ? "var(--font-cairo), sans-serif"
    : "var(--font-readex-pro), sans-serif";

  const bodyFont = isArabic
    ? "var(--font-cairo), serif"
    : "var(--font-work-sans), serif";

  const renderProductLinks = (category: any) => {
    const showProducts = category.products.slice(0, 5);
    const hasMore = category.products.length > 5;

    return (
      <>
        {showProducts.map((product: any) => (
          <Link
            as={NextLink}
            key={product.id}
            href={`/products/${product.slug}`}
            fontSize="sm"
            color="gray.600"
            _hover={{ textDecoration: "underline" }}
            fontFamily={bodyFont}
            textAlign={isMobile ? (isArabic ? "right" : "left") : "center"}
            w={"100%"}
          >
            {isArabic ? product.name_ar : product.name}
          </Link>
        ))}
        {hasMore && (
          <Link
            as={NextLink}
            href={`/category/${category.slug}`}
            fontSize="sm"
            color="#7ea2ca"
            fontWeight="medium"
            fontFamily={bodyFont}
            textAlign={isMobile ? (isArabic ? "right" : "left") : "center"}
            w={"100%"}
          >
            {isArabic ? "عرض الكل" : "View All"}
          </Link>
        )}
      </>
    );
  };

  const renderCategorySection = (category: any) => (
    <VStack key={category.id} align="start" spacing={2}>
      <Link href={`/category/${category.slug}`} w={"100%"}>
        <Text
          fontWeight="bold"
          fontSize="md"
          fontFamily={headingFont}
          textAlign={"center"}
        >
          {isArabic ? category.name_ar : category.name}
        </Text>
      </Link>
      {renderProductLinks(category)}
    </VStack>
  );

  return (
    <Box
      bg="gray.50"
      py={10}
      px={isMobile ? 4 : "15rem"}
      dir={isArabic ? "rtl" : "ltr"}
      textAlign={isArabic ? "right" : "left"}
    >
      <VStack spacing={10} align="stretch">
        {isMobile ? (
          <Accordion allowToggle>
            {categories
              .filter((category: any) => category.id !== 4)
              .map((category: any) => (
                <AccordionItem key={category.id} border="none">
                  <h2>
                    <AccordionButton fontWeight="bold" px={4} py={5}>
                      <Box
                        flex="1"
                        textAlign={isArabic ? "right" : "left"}
                        fontFamily={bodyFont}
                      >
                        {isArabic ? category.name_ar : category.name}
                      </Box>
                      <AccordionIcon />
                    </AccordionButton>
                  </h2>
                  <AccordionPanel pb={4} px={0}>
                    <VStack align="start" spacing={2} px={4}>
                      {renderProductLinks(category)}
                    </VStack>
                  </AccordionPanel>
                </AccordionItem>
              ))}
            <AccordionItem border="none">
              <h2>
                <AccordionButton fontWeight="bold" px={4} py={5}>
                  <Box
                    flex="1"
                    textAlign={isArabic ? "right" : "left"}
                    fontFamily={bodyFont}
                  >
                    {isArabic ? "الدعم" : "Support"}
                  </Box>
                  <AccordionIcon />
                </AccordionButton>
              </h2>
              <AccordionPanel pb={4} px={0}>
                <VStack align="start" spacing={2} px={4}>
                  <Link
                    as={NextLink}
                    href={"/contact-us"}
                    fontSize="sm"
                    color="gray.600"
                    _hover={{ textDecoration: "underline" }}
                    fontFamily={bodyFont}
                    textAlign={
                      isMobile ? (isArabic ? "right" : "left") : "center"
                    }
                    w={"100%"}
                  >
                    {isArabic ? "تواصل معنا" : "Contact Us"}
                  </Link>
                </VStack>
              </AccordionPanel>
            </AccordionItem>
            <HStack w={"100%"} justifyContent={"center"}>
              {socials.map((social: any) => (
                <Link
                  as={NextLink}
                  key={social.href}
                  href={social.href ?? "#"}
                  target="_blank"
                >
                  <IconButton
                    aria-label={social.href}
                    icon={social.icon}
                    colorScheme="brandPink2"
                    fontSize={"1.6rem"}
                    size={"sm"}
                    borderRadius={10}
                  />
                </Link>
              ))}
            </HStack>
          </Accordion>
        ) : (
          <SimpleGrid columns={{ base: 1, md: 3, lg: 4 }} spacing={10}>
            {categories
              .filter((category: any) => category.id !== 4)
              .map(renderCategorySection)}
            <VStack align="start" spacing={2}>
              <Link href={`/contact-us`} w={"100%"}>
                <Text
                  fontWeight="bold"
                  fontSize="md"
                  fontFamily={headingFont}
                  textAlign={"center"}
                >
                  {isArabic ? "الدعم" : "Support"}
                </Text>
              </Link>
              <Link
                as={NextLink}
                href={`/contact-us`}
                fontSize="sm"
                color="gray.600"
                _hover={{ textDecoration: "underline" }}
                fontFamily={bodyFont}
                textAlign={"center"}
                w={"100%"}
              >
                {isArabic ? "تواصل معنا" : "Contact Us"}
              </Link>
              <Text
                cursor={"pointer"}
                fontSize="sm"
                color="gray.600"
                _hover={{ textDecoration: "underline" }}
                fontFamily={bodyFont}
                textAlign={"center"}
                w={"100%"}
              >
                {isArabic ? "التواصل الاجتماعي" : "Our Socials"}
              </Text>
              <HStack w={"100%"} justifyContent={"center"}>
                {socials.map((social: any) => (
                  <Link
                    as={NextLink}
                    key={social.href}
                    href={social.href ?? "#"}
                    target="_blank"
                  >
                    <IconButton
                      aria-label={social.href}
                      icon={social.icon}
                      colorScheme="brandPink2"
                      fontSize={"1.6rem"}
                      size={"sm"}
                      borderRadius={10}
                    />
                  </Link>
                ))}
              </HStack>
            </VStack>
          </SimpleGrid>
        )}

        <Text
          fontSize="md"
          textAlign="center"
          color="gray.500"
          fontFamily={headingFont}
          dir="ltr"
        >
          © {new Date().getFullYear()} {brandName}
        </Text>
      </VStack>
    </Box>
  );
};

export default Footer;
