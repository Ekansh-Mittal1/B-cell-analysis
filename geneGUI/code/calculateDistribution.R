library(shazam)
args = commandArgs(trailingOnly = TRUE)

if (length(args)==0) {
  stop("At least one argument must be supplied (input file).n", call.=FALSE)
} else if (length(args)==1) {
  # default output file
  args[2] = "distributionPlot.png"
}

db = read.table(file = args[1], sep = '\t', header = TRUE)

db <- distToNearest(db, 
                          sequenceColumn="junction", 
                          vCallColumn="v_call", jCallColumn="j_call",
                          model="ham", normalize="len", nproc=1)


output <- findThreshold(db$dist_nearest, method="gmm", model="gamma-gamma", cutoff="user", spc=0.99)

print(output)

png(filename = args[2])
plot(output, binwidth=0.02, title=paste0(output@model, "   loglk=", output@loglk))
