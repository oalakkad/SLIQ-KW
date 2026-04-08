"use client";

import { useRouter } from "next/navigation";
import { useAppSelector, useAppDispatch } from "@/redux/hooks";
import { useLogoutMutation } from "@/redux/features/authApiSlice";
import { logout as setLogout } from "@/redux/features/authSlice";
import { useRetrieveUserQuery } from "@/redux/features/authApiSlice";
import {
  Box,
  Drawer,
  DrawerBody,
  DrawerCloseButton,
  DrawerContent,
  DrawerOverlay,
  Flex,
  IconButton,
  useDisclosure,
  useMediaQuery,
  Badge,
} from "@chakra-ui/react";
import { AnimatedLink } from "../animation/AnimatedLink";
import { AnimatedLinkWithDropdown } from "../animation/AnimatedLinkWithDropdown";
import { SlUser, SlBag } from "react-icons/sl";
import { BsBagFill } from "react-icons/bs";
import { PiHeartLight } from "react-icons/pi";
import { PiHeartFill } from "react-icons/pi";
import { CiSearch } from "react-icons/ci";
import Image from "next/image";
import saieLogo from "@/public/saie-logo.png";
import { useSiteSettings } from "@/hooks/use-site-settings";
import { HamburgerMenu } from "./HamburgerMenu";
import { HamburgerIcon } from "@chakra-ui/icons";
import SearchBox from "./SearchBox";
import Link from "next/link";
import { useCart } from "@/hooks/use-cart";
import { useWishlist } from "@/hooks/use-wishlist";
import { useMenuCategories } from "@/hooks/use-menu-categories";
import { buildDynamicMenu } from "./BuildDynamicMenu";
import { useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import LanguageSelector from "./LanguageSelector";

export default function Navbar() {
  const dispatch = useAppDispatch();
  const [isMobile] = useMediaQuery(["(max-width: 950px)"]);
  const { data: user } = useRetrieveUserQuery();
  const [logout] = useLogoutMutation();
  const { isAuthenticated } = useAppSelector((state) => state.auth);

  const { data: cart } = useCart();
  const { items: wishlistItems } = useWishlist();
  const cartCount = cart?.items.length || 0;
  const wishlistCount = wishlistItems?.length || 0;

  const router = useRouter();
  const queryClient = useQueryClient();

  const handleLogout = () => {
    logout(undefined)
      .unwrap()
      .then(() => {
        dispatch(setLogout());
        queryClient.removeQueries({ queryKey: ["cart"] });
        queryClient.removeQueries({ queryKey: ["wishlist"] });
        router.push("/");
      });
  };

  const { data: categories } = useMenuCategories();
  const isArabic = useAppSelector((state) => state.lang.isArabic);
  const baseMenu = [
    {
      id: "home",
      href: "/",
      name: isArabic ? "الصفحة الرئيسية" : "Home",
      children: null,
    },
    {
      id: "LOOKBOOK",
      href: "/lookbook",
      name: isArabic ? "سجل الصور" : "LOOKBOOK",
      children: null,
    },
    {
      id: "shop",
      href: "/shop",
      name: isArabic ? "المتجر" : "Shop",
      children: [],
    },
    {
      id: "kids",
      href: "/kids",
      name: isArabic ? "الأطفال" : "Kids",
      children: null,
    },
  ];

  const headingFont = isArabic
    ? "var(--font-cairo), sans-serif"
    : "var(--font-readex-pro), sans-serif";

  const bodyFont = isArabic
    ? "var(--font-cairo), serif"
    : "var(--font-work-sans), serif";

  const dynamicMenu = useMemo(() => {
    if (!categories) return baseMenu;
    const { shopChildren } = buildDynamicMenu(categories, isArabic);
    return baseMenu.map((item) =>
      item.id === "shop" ? { ...item, children: shopChildren } : item
    );
  }, [categories, isArabic]);

  const { data: siteSettings } = useSiteSettings();
  const logoSrc = siteSettings?.logo || saieLogo;

  const { isOpen, onOpen, onClose } = useDisclosure();
  const {
    isOpen: isSearchOpen,
    onOpen: onSearchOpen,
    onClose: onSearchClose,
  } = useDisclosure();

  return (
    <Flex
      bgColor={"white"}
      w={"100%"}
      minH={"60px"}
      gap={4}
      pb={6}
      pt={2}
      px={isMobile ? 2 : "100px"}
    >
      <SearchBox isOpen={isSearchOpen} onClose={onSearchClose} />

      <Flex flex={1} justifyContent={"flex-start"} alignItems={"center"}>
        {!isMobile && (
          <IconButton
            aria-label="search"
            icon={<CiSearch />}
            fontSize={"1.7rem"}
            variant={"link"}
            borderRadius={"50%"}
            _hover={{ color: "gray.300" }}
            onClick={onSearchOpen}
          />
        )}
        {isMobile && (
          <>
            <IconButton
              icon={<HamburgerIcon />}
              aria-label="Open menu"
              onClick={onOpen}
              variant="variant"
              fontSize={"xl"}
              _hover={{ color: "gray.300" }}
            />
            <Drawer isOpen={isOpen} placement="left" onClose={onClose}>
              <DrawerOverlay />
              <DrawerContent maxW="320px" pt={6}>
                <DrawerCloseButton top={4} right={4} />
                <DrawerBody px={4}>
                  <HamburgerMenu menu={dynamicMenu} onClose={onClose} />
                </DrawerBody>
              </DrawerContent>
            </Drawer>
          </>
        )}
      </Flex>

      <Flex
        flex={2}
        flexDir={"column"}
        justifyContent={"center"}
        alignItems={"center"}
      >
        <Box mt={4}></Box>
        <Link href={"/"}>
          <Image src={logoSrc} alt="SAIE" width={128} height={49} unoptimized={!!siteSettings?.logo} />
        </Link>
        <Flex flexDirection={"row"} mt={5} justifyContent={"space-evenly"}>
          {!isMobile &&
            dynamicMenu.map((item) =>
              item.children ? (
                <AnimatedLinkWithDropdown
                  key={item.id}
                  item={item}
                  isArabic={isArabic}
                  headingFont={headingFont}
                  bodyFont={bodyFont}
                />
              ) : (
                <AnimatedLink
                  fontColor={"gray.600"}
                  key={item.id}
                  name={item.name}
                  isArabic={isArabic}
                  href={item.href}
                  headingFont={headingFont}
                  bodyFont={bodyFont}
                />
              )
            )}
        </Flex>
      </Flex>

      <Flex flex={1} justifyContent={"flex-end"} alignItems={"center"} gap={1}>
        {isMobile && (
          <IconButton
            aria-label="search"
            icon={<CiSearch />}
            fontSize={"1.5rem"}
            p={2}
            border={"none"}
            variant={"outlineYellow"}
            onClick={onSearchOpen}
            borderRadius={"50%"}
          />
        )}

        {!isMobile && (
          <>
            <LanguageSelector />
            <Link href={isAuthenticated ? "/profile" : "/auth/login"}>
              <IconButton
                aria-label="user-profile"
                icon={<SlUser />}
                fontSize={"1.3rem"}
                p={2}
                border={"none"}
                bg="transparent"
                _hover={{ bg: "brand.yellow", color: "white" }}
                borderRadius={"50%"}
              />
            </Link>
          </>
        )}

        <Box position="relative">
          <Link href={isAuthenticated ? "/wishlist" : "/auth/login"}>
            <IconButton
              aria-label="wishlist"
              icon={wishlistCount > 0 ? <PiHeartFill /> : <PiHeartLight />}
              color={wishlistCount > 0 ? "#e6a1a8" : "gray.800"}
              fontSize="1.5rem"
              p={2}
              border="none"
              bg="transparent"
              _hover={{ bg: "brand.pink", color: "white" }}
              borderRadius="50%"
            />
          </Link>
          {wishlistCount > 0 && (
            <Badge
              position="absolute"
              top="-1"
              right="-1"
              bg="#e6a1a8"
              color="white"
              fontSize="0.7rem"
              borderRadius="full"
              w="18px"
              h="18px"
              display="flex"
              alignItems="center"
              justifyContent="center"
              zIndex="1"
            >
              {wishlistCount}
            </Badge>
          )}
        </Box>

        <Box position="relative">
          <Link href={"/cart"}>
            <IconButton
              aria-label="cart"
              icon={cartCount > 0 ? <BsBagFill /> : <SlBag />}
              fontSize={cartCount > 0 ? "1.2rem" : "1.3rem"}
              color={cartCount > 0 ? "#7ea2ca" : "gray.800"}
              p={2}
              border="none"
              bg="transparent"
              _hover={{ bg: "brand.blue", color: "white" }}
              borderRadius="50%"
            />
          </Link>
          {cartCount > 0 && (
            <Badge
              position="absolute"
              top="-1"
              right="-1"
              bg="#7ea2ca"
              color="white"
              fontSize="0.7rem"
              borderRadius="full"
              w="18px"
              h="18px"
              display="flex"
              alignItems="center"
              justifyContent="center"
              zIndex="1"
            >
              {cartCount}
            </Badge>
          )}
        </Box>
      </Flex>
    </Flex>
  );
}
