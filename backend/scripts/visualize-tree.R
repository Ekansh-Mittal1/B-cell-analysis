library(ape)

# Get command line arguments for outs directory
args <- commandArgs(trailingOnly = TRUE)
if (length(args) == 0) {
    outs_dir <- "outs"
} else {
    outs_dir <- args[1]
}

# Read newick tree files from trees directory
trees_dir <- file.path(outs_dir, "trees")

# Find all .newick files
newick_files <- list.files(trees_dir, pattern = "\\.newick$", full.names = TRUE)

if (length(newick_files) == 0) {
    warning("No newick tree files found")
    quit(status = 0)
}

# Plot each tree
for (i in seq_along(newick_files)) {
    tryCatch({
        # Read the newick tree
        tree <- read.tree(newick_files[i])
        
        # Get the basename without extension for output
        base_name <- basename(newick_files[i])
        base_name <- sub("\\.newick$", "", base_name)
        
        # Output PNG file
        png_file <- file.path(trees_dir, paste0(base_name, ".png"))
        
        # Root the tree if it's unrooted (root at the first tip for simplicity)
        if (!is.rooted(tree)) {
            # For unrooted trees, we can root at an outgroup (GERM sequence) if available
            germ_tips <- grep("GERM", tree$tip.label, ignore.case = TRUE)
            if (length(germ_tips) > 0) {
                tree <- root(tree, outgroup = tree$tip.label[germ_tips[1]], resolve.root = TRUE)
            } else {
                # Root at first tip if no GERM found
                tree <- root(tree, outgroup = tree$tip.label[1], resolve.root = TRUE)
            }
        }
        
        # Create plot with larger size
        png(png_file, width = 3200, height = 2200, res = 120)
        
        # Calculate maximum label length for proper spacing
        max_label_length <- max(nchar(tree$tip.label))
        
        # Set margins: bottom, left, top, right
        par(mar = c(4, 2, 4, 2))
        
        # First, plot tree invisibly to get the coordinate system
        plot(tree, 
             type = "phylogram",
             direction = "rightwards",
             show.tip.label = FALSE,
             edge.width = 3,
             plot = FALSE)
        
        # Get the last plot parameters
        last_plot <- get("last_plot.phylo", envir = .PlotPhyloEnv)
        
        # Calculate proper x limits
        # Tree depth + space for labels
        tree_depth <- max(last_plot$xx)
        label_space <- max_label_length * 0.015  # Space needed for labels
        x_max <- tree_depth + label_space
        
        # Now plot for real with proper limits
        plot(tree, 
             type = "phylogram",
             direction = "rightwards",
             main = paste("Phylogenetic Tree:", base_name),
             cex = 1.6,
             edge.width = 4,
             tip.color = "darkblue",
             label.offset = tree_depth * 0.02,
             show.node.label = FALSE,
             font = 1,
             adj = 0,
             x.lim = c(0, x_max),
             use.edge.length = TRUE)
        
        dev.off()
        
    }, error = function(e) {
        warning(paste("Failed to plot tree", i, ":", e$message))
    })
}

cat(paste("Generated", length(newick_files), "tree visualizations\n"))