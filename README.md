# blender Seams to Sewing pattern

An add-on for Blender 2.8 and 2.9 that assists with setting up 2D sewing patterns from 3D models, for cloth simulation and real-life sewing.

![](https://blenderartists.org/uploads/default/optimized/4X/3/7/9/379d4a76a9022a7ff338773500784e22500dd8f6_2_690x207.jpeg)
![](https://gitlab.com/thomaskole/blender-seams-to-sewing-pattern/-/wikis/uploads/2364f88e60b43cf0cc44309c2e4f15be/triceratops.gif)

# installation
Download the **Stable** archive here:\
https://gitlab.com/thomaskole/blender-seams-to-sewing-pattern/-/archive/master/blender-seams-to-sewing-pattern-master.zip

Or the **Experimental** archive here:\
https://gitlab.com/thomaskole/blender-seams-to-sewing-pattern/-/archive/work_in_progress/blender-seams-to-sewing-pattern-work_in_progress.zip

In Blender, go to `Edit > ⚙️ Preferences > Install..` and select the zip file you just downloaded.\
Enable the add-on in the list

# very brief overview:
`Object > Seams to Sewing Pattern > Seams to Sewing Pattern`\
turns your mesh into a sewing patten based on it's UV layout.

`Object > Seams to Sewing Pattern > Quick Clothsim`\
Applies some basic cloth sim options to your Object

`Object > Seams to Sewing Pattern > Export Sewing Pattern (.svg)`\
Exports your sewing pattern to a .SVG file for printing and sewing in real life.

`Edge > Clean up Knife Cut`\
Clean up selected edges after you used the knife tool on a mesh

# reporting issues
Something wrong? Please let me know.

There's a Blender Artists thread here: https://blenderartists.org/t/1248713 \
You can also add an issue here on GitLab,\
or get in touch with me otherwise: \
http://www.thomaskole.nl

# troubleshooting

**I'm getting a python error**\
That's bad, please let me know the error and how you triggered it.

**After unfolding, there's some weird long triangles /strips flying out**\
Most likely some non-manifold geometry, overlapping vertices, or bad normals.\
Disable the remesh option and see where it goes wrong in your mesh / UV'seams

**My mesh is imploding on itself during clothsim**\
Yeah, clothsim... Try balancing the "pressure" and "sewing force".\
It can help to keyframe the "pressure" to something very high on frame 1 and decrease over time.