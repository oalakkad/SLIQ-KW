"use client";

import {
  Box,
  Button,
  Flex,
  Heading,
  SimpleGrid,
  Spinner,
  Text,
  useMediaQuery,
} from "@chakra-ui/react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { useRetrieveUserQuery } from "@/redux/features/authApiSlice";

import HeroBanner from "@/components/common/HeroBanner";
import AboutSection from "@/components/common/AboutSection";
import CategoryCard from "@/components/common/CategoryCard";
import ThreeImages from "@/components/common/ThreeImages";

import type { ThreeImagesProps } from "@/components/common/ThreeImages";
import type { CategoryCardProps } from "@/components/common/CategoryCard";
import { useAppSelector } from "@/redux/hooks";
import { useSiteSettings } from "@/hooks/use-site-settings";

const API_URL = process.env.NEXT_PUBLIC_AWS_URL || "http://localhost:8000";

const generateImageSet = (start: number): ThreeImagesProps[] =>
  [0, 1, 2].map((i) => ({
    src: `${API_URL}/media/home/${start + i}.webp`,
    alt: `Image ${i + 1}`,
  }));

const imageGroups = [
  generateImageSet(1),
  generateImageSet(4),
  generateImageSet(7),
];

export default function Page() {
  const [isMobile] = useMediaQuery(["(max-width: 768px)"]);
  const { data: user } = useRetrieveUserQuery();
  const [loading, setLoading] = useState(true);
  const isArabic = useAppSelector((state) => state.lang.isArabic);
  const { data: siteSettings } = useSiteSettings();
  const direction = isArabic ? "rtl" : "ltr";
  const textAlign = isArabic ? "right" : "left";
  const marginX = isArabic ? { ml: 0, mr: 6 } : { ml: 6, mr: 0 };

  const categories: CategoryCardProps[] = [
    {
      title: isArabic ? "مشابك الشعر" : "HAIR CLIPS",
      imageUrl: `${API_URL}/media/home/hair-clips.jpg`,
      href: "/category/hair-clips",
    },
    {
      title: isArabic ? "فرش الشعر" : "HAIR BRUSHES",
      imageUrl: `${API_URL}/media/home/hair-brushes.jpg`,
      href: "/category/hair-brushes",
    },
    {
      title: isArabic ? "مشابك جاهزة" : "PRE-MADE CLIPS",
      imageUrl: `${API_URL}/media/home/premade-clips.png`,
      href: "/category/pre-made-clips",
    },
    {
      title: isArabic ? "حقائب المكياج" : "MAKEUP BAGS",
      imageUrl: `${API_URL}/media/home/makeup-bags.png`,
      href: "/category/makeup-pouches",
    },
  ];

  const kidsProducts: CategoryCardProps[] = [
    {
      title: isArabic ? "الأخضر السعيد" : "HAPPY GREEN",
      imageUrl: `${API_URL}/media/product-images/happy-green_SwXvMVa.png`,
      href: "/products/happy-green",
    },
    {
      title: isArabic ? "الدببة البنفسجية" : "PURPLE BEARS",
      imageUrl: `${API_URL}/media/product-images/purple-bears_h77mWmn.png`,
      href: "/products/purple-bear",
    },
    {
      title: isArabic ? "الدببة السعيد" : "HAPPY BEARS",
      imageUrl: `${API_URL}/media/product-images/happy-bear_Pb3cpaC.png`,
      href: "/products/happy-bear",
    },
    {
      title: isArabic ? "أسود وردي" : "BLACK PINK",
      imageUrl: `${API_URL}/media/product-images/black-pink_YVEYYbt.png`,
      href: "/products/black-pink",
    },
  ];

  const t = {
    shopNow: isArabic ? "تسوقي الآن" : "SHOP NOW",
    hairClipsTitle: isArabic ? "مشابك شعر عصرية" : "CLAW CLIPS",
    hairClipsDesc: isArabic
      ? "أضيفي لمسة فورية لإطلالتكِ مع مشابك أنيقة تناسب كل المناسبات."
      : "Elevate your look instantly with stylish hair clips made for every occasion.",

    hairBrushesTitle: isArabic ? "فرش شعر أساسية" : "ESSENTIAL HAIR BRUSHES",
    hairBrushesDesc: isArabic
      ? "اعتني بشعركِ مع مجموعة فرش عالية الجودة للتسريح اليومي والتصفيف المثالي."
      : "Care for your hair with premium brushes designed for everyday detangling and flawless styling.",

    makeupBagsTitle: isArabic ? "حقيبة مكياج أنيقة" : "MAKEUP BAGS",
    makeupBagsDesc: isArabic
      ? "احملي مستحضراتكِ المفضلة بأناقة مع حقائب عملية للسفر والاستخدام اليومي."
      : "Carry your beauty essentials in style with versatile makeup bags, perfect for travel or daily use.",

    shopCategory: isArabic ? "تسوقي حسب الفئة" : "SHOP BY CATEGORY",
    inspiredBy: isArabic ? "مستوحى من" : "INSPIRED BY",
    inspiredDesc: isArabic
      ? "مجموعة مستوحاة من الأيام المشمسة والإجازات الصغيرة ولمسات الأناقة اليومية."
      : "A collection inspired by sunlit days, weekend escapes, and effortless everyday elegance.",
    aboutUs: isArabic ? "من نحن" : "ABOUT US",
    aboutDesc: isArabic
      ? (siteSettings?.bio_ar || "علامة تجارية نسائية جريئة تدعمها منتجات عالية الجودة وفعالة وسهلة الاستخدام.")
      : (siteSettings?.bio_en || "A brand founded on bold femininity, offering effective and effortless products."),
    ourStory: isArabic ? "سجلنا" : "Our LOOKBOOK",
    kidsTitle: isArabic ? "الأطفال" : "KIDS",
  };

  const sections = [
    {
      bg: "brand.pink",
      title: t.hairClipsTitle,
      desc: t.hairClipsDesc,
      href: "/category/hair-clips",
    },
    {
      bg: "white",
      title: t.hairBrushesTitle,
      desc: t.hairBrushesDesc,
      href: "/category/hair-brushes",
    },
    {
      bg: "brand.pink",
      title: t.makeupBagsTitle,
      desc: t.makeupBagsDesc,
      href: "/category/makeup-bags",
    },
    {
      bg: "white",
      title: "",
      desc: "",
      href: "/shop",
    },
    {
      bg: "brand.blue",
      title: "",
      desc: "",
      href: "/shop",
    },
  ];

  useEffect(() => {
    const handlePageLoad = () => setLoading(false);
    if (document.readyState === "complete") handlePageLoad();
    else window.addEventListener("load", handlePageLoad);
    return () => window.removeEventListener("load", handlePageLoad);
  }, []);

  const headingFont = isArabic
    ? "var(--font-cairo), sans-serif"
    : "var(--font-readex-pro), sans-serif";

  const bodyFont = isArabic
    ? "var(--font-cairo), serif"
    : "var(--font-work-sans), serif";

  if (loading) {
    return (
      <Flex
        w="100vw"
        h="100vh"
        align="center"
        justify="center"
        bg="white"
        position="fixed"
        top={0}
        left={0}
        zIndex={9999}
      >
        <Spinner color="brand.pink" size="xl" thickness="4px" />
      </Flex>
    );
  }

  return (
    <Box dir={direction}>
      {imageGroups.slice(0, 5).map((images, i) => {
        const section = sections[i];

        return (
          <Box key={i} bg={section.bg} pt={20} pb={4} px={5}>
            <ThreeImages images={images} />

            <Box
              w={isMobile ? "90%" : "30%"}
              {...marginX}
              textAlign={textAlign}
            >
              {section.title && (
                <Heading
                  size="lg"
                  color="gray.500"
                  my={2}
                  fontFamily={headingFont}
                >
                  {section.title}
                </Heading>
              )}

              {section.desc && (
                <Text fontWeight={100} color="black" fontFamily={bodyFont}>
                  {section.desc}
                </Text>
              )}

              <Link href={section.href}>
                <Button
                  my={4}
                  variant="outline"
                  fontSize="sm"
                  fontFamily={headingFont}
                >
                  {t.shopNow}
                </Button>
              </Link>
            </Box>
          </Box>
        );
      })}

      <Box px={{ base: 4, md: 16 }} py={10}>
        <Heading
          color="gray.700"
          fontFamily={bodyFont}
          textAlign="center"
          size="lg"
          fontWeight={400}
          my={5}
        >
          {t.shopCategory}
        </Heading>
        <SimpleGrid columns={{ base: 2, md: 4 }} columnGap={6}>
          {categories.map((cat) => (
            <CategoryCard key={cat.title} {...cat} />
          ))}
        </SimpleGrid>
      </Box>

      <Box px={{ base: 4, md: 16 }} py={10} bg="brand.blue">
        <Heading
          color="gray.700"
          fontFamily={bodyFont}
          textAlign="center"
          size="lg"
          fontWeight={400}
          my={5}
        >
          {t.kidsTitle}
        </Heading>
        <SimpleGrid columns={{ base: 2, md: 4 }} columnGap={6}>
          {kidsProducts.map((cat) => (
            <CategoryCard key={cat.title} {...cat} />
          ))}
        </SimpleGrid>
      </Box>

      <HeroBanner
        title={t.inspiredBy}
        description={t.inspiredDesc}
        buttonText={t.shopNow}
        buttonLink="/shop"
        imageSrc={`${API_URL}/media/home/banner.svg`}
      />

      <AboutSection
        title={t.aboutUs}
        description={t.aboutDesc}
        buttonText={t.ourStory}
        buttonLink="/lookbook"
        imageSrc={`${API_URL}/media/home/banner2.svg`}
      />
    </Box>
  );
}
