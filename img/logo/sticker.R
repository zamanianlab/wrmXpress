#install.packages("hexSticker")
library("hexSticker")

library(magick)
library(pdftools)
library(grConvert)
library(grImport2)
library(tidyverse)
library(cowplot)

library(showtext)
## Loading Google fonts (http://www.google.com/fonts)
font_add_google("Raleway","raleway")

## Automatically use showtext to render text for future devices
showtext_auto()

gummy <- image_read("~/Desktop/gummy.png", density = 1200)
gummy <- ggdraw() +
  draw_image(gummy, scale = 1)

s <- sticker(~plot(gummy), package="wrmXpress", p_size=7, p_y=1.4, s_x=0.95, s_y=0.75, s_width=1.2, s_height=1.1,
             h_fill="#3b4d61", h_color="#ffc13b", p_family = "raleway", p_fontface = "bold",
             filename="~/Desktop/logo.png")

