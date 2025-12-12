library(alakazam)
library(ape)

db = readIgphyml("build-trees-input_igphyml-pass.tab",format="phylo")

#plot largest lineage tree
for(x in 1:length(db$trees[])){

    y = paste("trees/tree", x, ".png", sep = "")
    png(y)
    plot(db$trees[[x]])

}
#plot(db$trees[[1]])
#plot(db$trees[[2]])

dev.off()